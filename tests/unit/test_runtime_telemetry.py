"""Unit tests for runtime log timing and provider activity feedback."""

from __future__ import annotations

import io
import time
from pathlib import Path
from threading import Event, Lock, Thread
from typing import TextIO, cast

import pytest

from bookvoice.config import BookvoiceConfig
from bookvoice.models.datatypes import Chunk, TranslationResult
from bookvoice.pipeline import BookvoicePipeline
from bookvoice.provider_factory import ProviderFactory
from bookvoice.telemetry.logger import RunLogger


class _ThreadSafeTextSink:
    """Thread-safe text sink for activity pulses emitted from worker threads."""

    def __init__(self) -> None:
        """Initialize in-memory storage and write lock."""

        self._buffer = io.StringIO()
        self._lock = Lock()

    def write(self, value: str) -> int:
        """Write text to the sink and return the number of characters accepted."""

        with self._lock:
            return self._buffer.write(value)

    def flush(self) -> None:
        """Flush the in-memory sink."""

        return None

    def getvalue(self) -> str:
        """Return the current sink content."""

        with self._lock:
            return self._buffer.getvalue()


class _BlockingTranslator:
    """Translator test double that blocks until the test releases it."""

    def __init__(self, started: Event, release: Event) -> None:
        """Initialize synchronization events."""

        self._started = started
        self._release = release

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Block during translation and then return deterministic text."""

        self._started.set()
        if not self._release.wait(timeout=1.0):
            raise AssertionError("translator release event was not set")
        return TranslationResult(
            chunk=chunk,
            translated_text=f"{target_language}: translated",
            provider="openai",
            model="test-model",
        )


def test_run_logger_emits_elapsed_and_stage_duration() -> None:
    """RunLogger should include deterministic elapsed and duration tokens."""

    clock_values = iter([10.0, 10.0, 10.0, 12.5, 12.5])

    def _clock() -> float:
        """Return deterministic monotonic clock values."""

        return next(clock_values)

    sink = io.StringIO()
    logger = RunLogger(sink=sink, clock=_clock)

    logger.log_stage_start("translate")
    logger.log_stage_complete("translate")

    output = sink.getvalue()
    assert "[phase] level=INFO stage=translate event=start elapsed=0.000s" in output
    assert (
        "[phase] level=INFO stage=translate event=complete "
        "duration=2.500s elapsed=2.500s"
    ) in output


def test_translate_stage_emits_activity_while_provider_call_is_running(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Translate stage should emit activity before a long provider call returns."""

    started = Event()
    release = Event()
    sink = _ThreadSafeTextSink()
    translator = _BlockingTranslator(started=started, release=release)

    def _create_translator(
        provider_id: str,
        model: str,
        api_key: str | None = None,
    ) -> _BlockingTranslator:
        """Return the blocking translator test double."""

        _ = provider_id, model, api_key
        return translator

    monkeypatch.setattr(ProviderFactory, "create_translator", _create_translator)

    pipeline = BookvoicePipeline(
        run_logger=RunLogger(sink=cast(TextIO, sink)),
        provider_activity_interval_seconds=0.01,
    )
    config = BookvoiceConfig(
        input_pdf=Path("input.pdf"),
        output_dir=tmp_path,
        api_key="test-key",
    )
    chunk = Chunk(
        chapter_index=1,
        chunk_index=0,
        text="Source text.",
        char_start=0,
        char_end=12,
    )
    results: list[list[TranslationResult]] = []

    def _run_translate() -> None:
        """Run translate stage in a thread so the test can observe in-flight logs."""

        results.append(pipeline._translate([chunk], config))

    translate_thread = Thread(target=_run_translate)
    translate_thread.start()
    assert started.wait(timeout=1.0)

    deadline = time.monotonic() + 1.0
    activity_output = ""
    while time.monotonic() < deadline:
        activity_output = sink.getvalue()
        if "[phase] level=INFO stage=translate event=activity" in activity_output:
            break
        time.sleep(0.005)

    assert "[phase] level=INFO stage=translate event=activity" in activity_output
    assert "item=1/1" in activity_output

    release.set()
    translate_thread.join(timeout=1.0)

    assert not translate_thread.is_alive()
    assert results[0][0].translated_text == "cs: translated"

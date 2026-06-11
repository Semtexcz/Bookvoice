"""Unit tests for ordered bounded provider-stage execution."""

from __future__ import annotations

from pathlib import Path
import time

import pytest

from bookvoice.config import BookvoiceConfig
from bookvoice.errors import PipelineStageError
from bookvoice.models.datatypes import AudioPart, Chunk, RewriteResult, TranslationResult
from bookvoice.pipeline.concurrency import run_ordered_bounded
from bookvoice.pipeline.orchestrator import BookvoicePipeline
from bookvoice.tts.voices import VoiceProfile


def _chunks() -> list[Chunk]:
    """Return deterministic chunk fixtures for provider ordering tests."""

    return [
        Chunk(
            chapter_index=1,
            chunk_index=index,
            text=f"source-{index}",
            char_start=index,
            char_end=index + 1,
            part_index=index + 1,
            part_title="Chapter",
            part_id=f"001_{index + 1:02d}_chapter",
        )
        for index in range(3)
    ]


class SlowTranslator:
    """Translator fake that completes later items first."""

    retry_attempt_count = 0
    cache_hits = 0
    cache_misses = 0

    def translate(self, chunk: Chunk, target_language: str) -> TranslationResult:
        """Return a translation after a chunk-dependent delay."""

        time.sleep(0.01 * (3 - chunk.chunk_index))
        return TranslationResult(
            chunk=chunk,
            translated_text=f"{target_language}-{chunk.chunk_index}",
            provider="openai",
            model="fake-translate",
        )


class SlowRewriter:
    """Rewriter fake that completes later items first."""

    retry_attempt_count = 0
    cache_hits = 0
    cache_misses = 0

    def rewrite(self, translation: TranslationResult) -> RewriteResult:
        """Return a rewrite after a chunk-dependent delay."""

        time.sleep(0.01 * (3 - translation.chunk.chunk_index))
        return RewriteResult(
            translation=translation,
            rewritten_text=f"rewrite-{translation.chunk.chunk_index}",
            provider="openai",
            model="fake-rewrite",
        )


class SlowSynthesizer:
    """TTS fake that completes later items first."""

    retry_attempt_count = 0

    def synthesize(self, rewrite: RewriteResult, voice: VoiceProfile) -> AudioPart:
        """Return an audio part after a chunk-dependent delay."""

        chunk = rewrite.translation.chunk
        time.sleep(0.01 * (3 - chunk.chunk_index))
        return AudioPart(
            chapter_index=chunk.chapter_index,
            chunk_index=chunk.chunk_index,
            path=Path(f"{chunk.chunk_index}.wav"),
            duration_seconds=1.0,
            part_index=chunk.part_index,
            part_title=chunk.part_title,
            part_id=chunk.part_id,
            provider="openai",
            model="fake-tts",
            voice=voice.provider_voice_id,
        )


def test_provider_stages_preserve_order_with_out_of_order_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Translate, rewrite, and TTS should return results in original chunk order."""

    monkeypatch.setattr(
        "bookvoice.pipeline.execution.ProviderFactory.create_translator",
        lambda **_: SlowTranslator(),
    )
    monkeypatch.setattr(
        "bookvoice.pipeline.execution.ProviderFactory.create_rewriter",
        lambda **_: SlowRewriter(),
    )
    monkeypatch.setattr(
        "bookvoice.pipeline.execution.ProviderFactory.create_tts_synthesizer",
        lambda **_: SlowSynthesizer(),
    )

    config = BookvoiceConfig(
        input_pdf=Path("input.pdf"),
        output_dir=tmp_path,
        max_provider_workers=3,
    )
    pipeline = BookvoicePipeline()
    chunks = _chunks()

    translations = pipeline._translate(chunks, config)
    rewrites = pipeline._rewrite_for_audio(translations, config)
    audio_parts = pipeline._tts(
        rewrites,
        config,
        store=type("Store", (), {"root": tmp_path})(),
    )

    assert [item.chunk.chunk_index for item in translations] == [0, 1, 2]
    assert [item.translation.chunk.chunk_index for item in rewrites] == [0, 1, 2]
    assert [item.chunk_index for item in audio_parts] == [0, 1, 2]


def test_ordered_bounded_worker_errors_include_stage_and_item_context() -> None:
    """Concurrent worker failures should identify the failed stage and item."""

    with pytest.raises(PipelineStageError) as exc_info:
        run_ordered_bounded(
            stage_name="translate",
            items=[1, 2, 3],
            max_workers=2,
            worker=lambda index, item: (_ for _ in ()).throw(
                RuntimeError(f"bad item {item}")
            )
            if index == 1
            else item,
        )

    assert exc_info.value.stage == "translate"
    assert "Provider item 2/3 failed during `translate`" in exc_info.value.detail

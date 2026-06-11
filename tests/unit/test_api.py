"""Unit tests for the public Python API facade."""

from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from bookvoice.api import (
    ProgressCallback,
    build_audiobook,
    create_build_config,
    list_chapters,
    list_chapters_from_artifact,
    resume_audiobook,
    run_chapters_only,
    run_translate_only,
    run_tts_only,
)
from bookvoice.config import BookvoiceConfig
from bookvoice.models.datatypes import BookMeta, Chapter, RunManifest


def _manifest_stub() -> RunManifest:
    """Return a deterministic manifest used by API facade tests."""

    return RunManifest(
        run_id="run-api",
        config_hash="cfg-api",
        book=BookMeta(
            source_pdf=Path("input.pdf"),
            title="API Fixture",
            author=None,
            language="cs",
        ),
        merged_audio_path=Path("out/run-api/audio/bookvoice_merged.wav"),
        total_llm_cost_usd=0.0,
        total_tts_cost_usd=0.0,
        total_cost_usd=0.0,
    )


def test_build_audiobook_delegates_to_pipeline_and_returns_manifest(
    monkeypatch: MonkeyPatch,
) -> None:
    """The public API should pass config/callback through to the pipeline."""

    manifest = _manifest_stub()
    captured: dict[str, object] = {}

    class FakePipeline:
        """Capture constructor and run inputs for the facade test."""

        def __init__(
            self,
            stage_progress_callback: ProgressCallback | None = None,
        ) -> None:
            captured["progress_callback"] = stage_progress_callback

        def run(self, config: BookvoiceConfig) -> RunManifest:
            captured["config"] = config
            return manifest

    monkeypatch.setattr("bookvoice.api.BookvoicePipeline", FakePipeline)

    config = BookvoiceConfig(input_pdf=Path("input.pdf"), output_dir=Path("out"))

    def progress_callback(stage_name: str, stage_index: int, stage_total: int) -> None:
        captured["progress_event"] = (stage_name, stage_index, stage_total)

    result = build_audiobook(config, progress_callback=progress_callback)

    assert result is manifest
    assert captured["config"] is config
    assert captured["progress_callback"] is progress_callback


def test_run_chapters_only_delegates_to_pipeline(monkeypatch: MonkeyPatch) -> None:
    """Chapters-only API should pass config/callback through to the pipeline."""

    manifest = _manifest_stub()
    captured: dict[str, object] = {}

    class FakePipeline:
        """Capture chapters-only constructor and run inputs."""

        def __init__(
            self,
            stage_progress_callback: ProgressCallback | None = None,
        ) -> None:
            captured["progress_callback"] = stage_progress_callback

        def run_chapters_only(self, config: BookvoiceConfig) -> RunManifest:
            captured["config"] = config
            return manifest

    monkeypatch.setattr("bookvoice.api.BookvoicePipeline", FakePipeline)

    config = BookvoiceConfig(input_pdf=Path("input.pdf"), output_dir=Path("out"))

    def progress_callback(stage_name: str, stage_index: int, stage_total: int) -> None:
        captured["progress_event"] = (stage_name, stage_index, stage_total)

    result = run_chapters_only(config, progress_callback=progress_callback)

    assert result is manifest
    assert captured["config"] is config
    assert captured["progress_callback"] is progress_callback


def test_run_translate_only_delegates_to_pipeline(monkeypatch: MonkeyPatch) -> None:
    """Translate-only API should pass config/callback through to the pipeline."""

    manifest = _manifest_stub()
    captured: dict[str, object] = {}

    class FakePipeline:
        """Capture translate-only constructor and run inputs."""

        def __init__(
            self,
            stage_progress_callback: ProgressCallback | None = None,
        ) -> None:
            captured["progress_callback"] = stage_progress_callback

        def run_translate_only(self, config: BookvoiceConfig) -> RunManifest:
            captured["config"] = config
            return manifest

    monkeypatch.setattr("bookvoice.api.BookvoicePipeline", FakePipeline)

    config = BookvoiceConfig(input_pdf=Path("input.pdf"), output_dir=Path("out"))

    def progress_callback(stage_name: str, stage_index: int, stage_total: int) -> None:
        captured["progress_event"] = (stage_name, stage_index, stage_total)

    result = run_translate_only(config, progress_callback=progress_callback)

    assert result is manifest
    assert captured["config"] is config
    assert captured["progress_callback"] is progress_callback


def test_run_tts_only_delegates_to_pipeline(monkeypatch: MonkeyPatch) -> None:
    """TTS-only API should pass manifest path/callback through to the pipeline."""

    manifest = _manifest_stub()
    captured: dict[str, object] = {}

    class FakePipeline:
        """Capture TTS-only constructor and manifest path input."""

        def __init__(
            self,
            stage_progress_callback: ProgressCallback | None = None,
        ) -> None:
            captured["progress_callback"] = stage_progress_callback

        def run_tts_only_from_manifest(self, manifest_path: Path) -> RunManifest:
            captured["manifest_path"] = manifest_path
            return manifest

    monkeypatch.setattr("bookvoice.api.BookvoicePipeline", FakePipeline)

    manifest_path = Path("out/run-api/run_manifest.json")

    def progress_callback(stage_name: str, stage_index: int, stage_total: int) -> None:
        captured["progress_event"] = (stage_name, stage_index, stage_total)

    result = run_tts_only(manifest_path, progress_callback=progress_callback)

    assert result is manifest
    assert captured["manifest_path"] == manifest_path
    assert captured["progress_callback"] is progress_callback


def test_resume_audiobook_delegates_to_pipeline(monkeypatch: MonkeyPatch) -> None:
    """Resume API should pass manifest path/callback through to the pipeline."""

    manifest = _manifest_stub()
    captured: dict[str, object] = {}

    class FakePipeline:
        """Capture resume constructor and manifest path input."""

        def __init__(
            self,
            stage_progress_callback: ProgressCallback | None = None,
        ) -> None:
            captured["progress_callback"] = stage_progress_callback

        def resume(self, manifest_path: Path) -> RunManifest:
            captured["manifest_path"] = manifest_path
            return manifest

    monkeypatch.setattr("bookvoice.api.BookvoicePipeline", FakePipeline)

    manifest_path = Path("out/run-api/run_manifest.json")

    def progress_callback(stage_name: str, stage_index: int, stage_total: int) -> None:
        captured["progress_event"] = (stage_name, stage_index, stage_total)

    result = resume_audiobook(manifest_path, progress_callback=progress_callback)

    assert result is manifest
    assert captured["manifest_path"] == manifest_path
    assert captured["progress_callback"] is progress_callback


def test_list_chapters_delegates_to_pipeline(monkeypatch: MonkeyPatch) -> None:
    """List-chapters API should expose detected chapter metadata."""

    chapter = Chapter(index=1, title="One", text="Text.")
    expected = ([chapter], "outline", "")
    captured: dict[str, object] = {}

    class FakePipeline:
        """Capture list-chapters constructor and config input."""

        def __init__(
            self,
            stage_progress_callback: ProgressCallback | None = None,
        ) -> None:
            captured["progress_callback"] = stage_progress_callback

        def list_chapters_from_source(
            self,
            config: BookvoiceConfig,
        ) -> tuple[list[Chapter], str, str]:
            captured["config"] = config
            return expected

    monkeypatch.setattr("bookvoice.api.BookvoicePipeline", FakePipeline)

    config = BookvoiceConfig(input_pdf=Path("input.pdf"), output_dir=Path("out"))

    result = list_chapters(config)

    assert result == expected
    assert captured["config"] is config
    assert captured["progress_callback"] is None


def test_list_chapters_from_artifact_delegates_to_pipeline(
    monkeypatch: MonkeyPatch,
) -> None:
    """Artifact list-chapters API should expose persisted chapter metadata."""

    chapter = Chapter(index=1, title="One", text="Text.")
    expected = ([chapter], "artifact", "")
    captured: dict[str, object] = {}

    class FakePipeline:
        """Capture artifact list constructor and artifact path input."""

        def __init__(
            self,
            stage_progress_callback: ProgressCallback | None = None,
        ) -> None:
            captured["progress_callback"] = stage_progress_callback

        def list_chapters_from_artifact(
            self,
            chapters_artifact: Path,
        ) -> tuple[list[Chapter], str, str]:
            captured["chapters_artifact"] = chapters_artifact
            return expected

    monkeypatch.setattr("bookvoice.api.BookvoicePipeline", FakePipeline)

    chapters_artifact = Path("out/run-api/text/chapters.json")

    result = list_chapters_from_artifact(chapters_artifact)

    assert result == expected
    assert captured["chapters_artifact"] == chapters_artifact
    assert captured["progress_callback"] is None


def test_public_api_imports_library_entry_points() -> None:
    """Library callers should be able to import stable public API functions."""

    from bookvoice.api import build_audiobook as imported_build_audiobook
    from bookvoice.api import list_chapters as imported_list_chapters
    from bookvoice.api import (
        list_chapters_from_artifact as imported_list_chapters_from_artifact,
    )
    from bookvoice.api import resume_audiobook as imported_resume_audiobook
    from bookvoice.api import run_chapters_only as imported_run_chapters_only
    from bookvoice.api import run_translate_only as imported_run_translate_only
    from bookvoice.api import run_tts_only as imported_run_tts_only

    assert imported_build_audiobook is build_audiobook
    assert imported_run_chapters_only is run_chapters_only
    assert imported_run_translate_only is run_translate_only
    assert imported_run_tts_only is run_tts_only
    assert imported_resume_audiobook is resume_audiobook
    assert imported_list_chapters is list_chapters
    assert imported_list_chapters_from_artifact is list_chapters_from_artifact


def test_create_build_config_uses_format_neutral_input_name() -> None:
    """The helper should hide the legacy `input_pdf` field name from callers."""

    config = create_build_config(
        input_path=Path("book.epub"),
        output_dir=Path("out"),
        language="en",
        chapter_selection="1-3",
        rewrite_bypass=True,
        max_provider_workers=2,
        extra={"packaging_output_format": "m4a"},
    )

    assert config.input_pdf == Path("book.epub")
    assert config.input_path == Path("book.epub")
    assert config.output_dir == Path("out")
    assert config.language == "en"
    assert config.chapter_selection == "1-3"
    assert config.rewrite_bypass is True
    assert config.max_provider_workers == 2
    assert config.extra == {"packaging_output_format": "m4a"}

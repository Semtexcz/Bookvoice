"""Unit tests for deterministic translation/rewrite artifact payload builders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from bookvoice.config import ProviderRuntimeConfig
from bookvoice.errors import PipelineStageError
from bookvoice.models.datatypes import Chapter, Chunk, RewriteResult, TranslationResult
from bookvoice.pipeline.artifacts import (
    load_translated_document,
    rewrite_artifact_payload,
    translated_document_artifact_payload,
    translation_artifact_payload,
)


def test_translation_and_rewrite_payload_builders_share_expected_schema() -> None:
    """Artifact builders should emit the persisted translation/rewrite JSON schema."""

    chapter_scope = {
        "chapter_scope_mode": "selected",
        "chapter_scope_label": "1-2",
        "chapter_scope_indices_csv": "1,2",
    }
    runtime_config = ProviderRuntimeConfig(
        translator_provider="openai",
        rewriter_provider="openai",
        tts_provider="openai",
        translate_model="gpt-4.1-mini",
        rewrite_model="gpt-4.1-mini",
        tts_model="gpt-4o-mini-tts",
        tts_voice="echo",
    )
    chunk = Chunk(
        chapter_index=1,
        chunk_index=0,
        text="Original chapter text.",
        char_start=0,
        char_end=22,
    )
    translation = TranslationResult(
        chunk=chunk,
        translated_text="Prelozeny text.",
        provider="openai",
        model="gpt-4.1-mini",
    )
    rewrite = RewriteResult(
        translation=translation,
        rewritten_text="Audio friendly text.",
        provider="openai",
        model="gpt-4.1-mini",
    )

    translations_payload = translation_artifact_payload(
        [translation],
        chapter_scope=chapter_scope,
        runtime_config=runtime_config,
    )
    rewrites_payload = rewrite_artifact_payload(
        [rewrite],
        chapter_scope=chapter_scope,
        runtime_config=runtime_config,
    )
    translations_payload_dict = cast(dict[str, Any], translations_payload)
    rewrites_payload_dict = cast(dict[str, Any], rewrites_payload)
    translations_list = cast(list[dict[str, Any]], translations_payload_dict["translations"])
    rewrites_list = cast(list[dict[str, Any]], rewrites_payload_dict["rewrites"])
    translation_metadata = cast(dict[str, Any], translations_payload_dict["metadata"])
    rewrite_metadata = cast(dict[str, Any], rewrites_payload_dict["metadata"])
    rewrite_translation = cast(dict[str, Any], rewrites_list[0]["translation"])

    assert set(translations_payload_dict.keys()) == {"translations", "metadata"}
    assert set(translations_list[0].keys()) == {
        "chunk",
        "translated_text",
        "provider",
        "model",
    }
    assert set(translation_metadata.keys()) == {
        "chapter_scope",
        "provider",
        "model",
    }
    assert set(rewrites_payload_dict.keys()) == {"rewrites", "metadata"}
    assert set(rewrites_list[0].keys()) == {
        "translation",
        "rewritten_text",
        "provider",
        "model",
    }
    assert set(rewrite_translation.keys()) == {
        "chunk",
        "translated_text",
        "provider",
        "model",
    }
    assert set(rewrite_metadata.keys()) == {
        "chapter_scope",
        "provider",
        "model",
        "rewrite_bypass",
    }


def test_translated_document_payload_and_loader_roundtrip(tmp_path: Path) -> None:
    """Translated-document artifact should serialize deterministically and load back."""

    chapters = [
        Chapter(index=2, title="Chapter 2", text="source-chapter-2"),
        Chapter(index=1, title="Chapter 1", text="source-chapter-1"),
    ]
    translations = [
        TranslationResult(
            chunk=Chunk(
                chapter_index=1,
                chunk_index=1,
                text="chunk-b",
                char_start=11,
                char_end=20,
            ),
            translated_text="Second translated paragraph.",
            provider="openai",
            model="gpt-4.1-mini",
        ),
        TranslationResult(
            chunk=Chunk(
                chapter_index=1,
                chunk_index=0,
                text="chunk-a",
                char_start=0,
                char_end=10,
            ),
            translated_text="First translated paragraph.",
            provider="openai",
            model="gpt-4.1-mini",
        ),
        TranslationResult(
            chunk=Chunk(
                chapter_index=2,
                chunk_index=0,
                text="chunk-c",
                char_start=0,
                char_end=8,
            ),
            translated_text="Chapter two translated paragraph.",
            provider="openai",
            model="gpt-4.1-mini",
        ),
    ]
    chapter_scope = {
        "chapter_scope_mode": "selected",
        "chapter_scope_label": "1-2",
        "chapter_scope_indices_csv": "1,2",
    }

    payload = translated_document_artifact_payload(
        chapters=chapters,
        translations=translations,
        source_format="epub",
        source_path=Path("tests/files/canonical_synthetic_fixture.epub"),
        target_language="cs",
        chapter_scope=chapter_scope,
    )
    artifact_path = tmp_path / "translated_document.json"
    artifact_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    loaded = load_translated_document(artifact_path)

    assert [chapter.index for chapter in loaded.chapters] == [1, 2]
    assert loaded.chapters[0].title == "Chapter 1"
    assert loaded.chapters[0].body == (
        "First translated paragraph.\n\nSecond translated paragraph."
    )
    assert loaded.chapters[1].title == "Chapter 2"
    assert loaded.chapters[1].body == "Chapter two translated paragraph."
    assert loaded.source_format == "epub"
    assert loaded.source_path == Path("tests/files/canonical_synthetic_fixture.epub")
    assert loaded.target_language == "cs"
    assert loaded.chapter_scope["chapter_scope_mode"] == "selected"


def test_load_translated_document_rejects_unordered_chapter_indices(
    tmp_path: Path,
) -> None:
    """Translated-document loader should fail when chapter order is not strictly increasing."""

    artifact_path = tmp_path / "translated_document.json"
    artifact_path.write_text(
        json.dumps(
            {
                "chapters": [
                    {"index": 2, "title": "Second", "body": "body"},
                    {"index": 1, "title": "First", "body": "body"},
                ],
                "metadata": {
                    "source_format": "pdf",
                    "source_path": "input.pdf",
                    "target_language": "cs",
                    "chapter_scope": {"chapter_scope_mode": "selected"},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PipelineStageError, match="strictly ordered"):
        load_translated_document(artifact_path)

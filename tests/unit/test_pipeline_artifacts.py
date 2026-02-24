"""Unit tests for deterministic translation/rewrite artifact payload builders."""

from __future__ import annotations

from typing import Any, cast

from bookvoice.config import ProviderRuntimeConfig
from bookvoice.models.datatypes import Chunk, RewriteResult, TranslationResult
from bookvoice.pipeline.artifacts import rewrite_artifact_payload, translation_artifact_payload


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

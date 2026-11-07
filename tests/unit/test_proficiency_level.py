"""Offline tests for optional CEFR proficiency-level control."""

from __future__ import annotations

import pytest

from bookvoice.llm.audio_rewriter import AudioRewriter, DeterministicBypassRewriter
from bookvoice.llm.openai_client import OpenAIChatClient
from bookvoice.llm.proficiency import (
    SUPPORTED_PROFICIENCY_LEVELS,
    normalize_proficiency_level,
)
from bookvoice.llm.prompts import PromptLibrary
from bookvoice.llm.translator import OpenAITranslator
from bookvoice.models.datatypes import Chunk, TranslationResult


def _install_recording_chat(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """Replace provider calls with a deterministic recorder and return its call list."""

    calls: list[dict[str, object]] = []

    def _record_chat(self, **kwargs: object) -> str:
        """Record one provider call and return deterministic text."""

        _ = self
        calls.append(kwargs)
        return f"response-{len(calls)}"

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _record_chat)
    return calls


def _user_prompt(calls: list[dict[str, object]], index: int) -> str:
    """Return the recorded user prompt for one provider call."""

    prompt = calls[index]["user_prompt"]
    assert isinstance(prompt, str)
    return prompt


def _chunk() -> Chunk:
    """Build a deterministic source chunk for translation tests."""

    return Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12)


def _translation() -> TranslationResult:
    """Build a deterministic translation result for rewrite tests."""

    return TranslationResult(
        chunk=_chunk(),
        translated_text="Ahoj svete.",
        provider="openai",
        model="gpt-4.1-mini",
    )


@pytest.mark.parametrize("level", SUPPORTED_PROFICIENCY_LEVELS)
def test_normalize_accepts_every_supported_level_case_insensitively(level: str) -> None:
    """Every CEFR label should normalize from lower, upper, and mixed case."""

    assert normalize_proficiency_level(level.lower()) == level
    assert normalize_proficiency_level(level) == level
    assert normalize_proficiency_level(f" {level.title()} ") == level


def test_normalize_returns_none_when_level_is_omitted() -> None:
    """Omitting the level should preserve the legacy path."""

    assert normalize_proficiency_level(None) is None


def test_normalize_rejects_unsupported_level_with_supported_labels() -> None:
    """Unsupported labels should fail with a diagnostic that names every valid label."""

    with pytest.raises(ValueError, match="Unsupported proficiency level 'D1'") as exc_info:
        normalize_proficiency_level("D1")

    for level in SUPPORTED_PROFICIENCY_LEVELS:
        assert level in str(exc_info.value)


def test_translation_prompt_includes_normalized_level_and_preservation() -> None:
    """Translation prompt should carry the normalized level and preservation rules."""

    prompt = PromptLibrary().translate_prompt(
        source_text="Hello world.",
        target_language="cs",
        proficiency_level="b1",
    )

    assert "Target CEFR proficiency level B1" in prompt
    assert "Preserve meaning, factual information, names, and numbers" in prompt


def test_translation_prompt_is_unchanged_when_level_is_omitted() -> None:
    """Omitted level should produce the exact legacy translation prompt."""

    prompt = PromptLibrary().translate_prompt(
        source_text="Hello world.",
        target_language="cs",
    )

    assert prompt == (
        "Translate the following text into cs while preserving meaning, "
        "tone, and paragraph structure. Output only the translated text.\n\n"
        "Hello world."
    )


def test_translator_cache_is_isolated_by_normalized_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Different levels should miss the cache, while case variants share an entry."""

    calls = _install_recording_chat(monkeypatch)
    translator = OpenAITranslator(model="gpt-4.1-mini", provider_id="openai", api_key="key")

    first = translator.translate(_chunk(), target_language="cs", proficiency_level="A2")
    second = translator.translate(_chunk(), target_language="cs", proficiency_level="a2")
    third = translator.translate(_chunk(), target_language="cs", proficiency_level="C1")

    assert len(calls) == 2
    assert first.translated_text == "response-1"
    assert second.translated_text == "response-1"
    assert third.translated_text == "response-2"
    assert "Target CEFR proficiency level A2" in _user_prompt(calls, 0)
    assert "Target CEFR proficiency level C1" in _user_prompt(calls, 1)


def test_translator_legacy_cache_and_prompt_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitted level should keep one prompt shape and one cache entry."""

    calls = _install_recording_chat(monkeypatch)
    translator = OpenAITranslator(model="gpt-4.1-mini", provider_id="openai", api_key="key")

    first = translator.translate(_chunk(), target_language="cs")
    second = translator.translate(_chunk(), target_language="cs")

    assert len(calls) == 1
    assert first.translated_text == second.translated_text
    assert "CEFR" not in _user_prompt(calls, 0)


def test_translator_rejects_invalid_level_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid levels should fail deterministically without a provider request."""

    calls = _install_recording_chat(monkeypatch)
    translator = OpenAITranslator(model="gpt-4.1-mini", provider_id="openai", api_key="key")

    with pytest.raises(ValueError, match="Unsupported proficiency level"):
        translator.translate(_chunk(), target_language="cs", proficiency_level="Z9")

    assert calls == []


def test_rewrite_prompt_includes_normalized_level_and_preservation() -> None:
    """Rewrite prompt should carry the normalized level and preservation rules."""

    prompt = PromptLibrary().rewrite_for_audio_prompt(
        translated_text="Ahoj svete.",
        proficiency_level="a1",
    )

    assert "Target CEFR proficiency level A1" in prompt
    assert "Preserve meaning, factual information, names, and numbers" in prompt


def test_rewrite_prompt_is_unchanged_when_level_is_omitted() -> None:
    """Omitted level should produce the exact legacy rewrite prompt."""

    prompt = PromptLibrary().rewrite_for_audio_prompt(translated_text="Ahoj svete.")

    assert prompt == (
        "Rewrite the following text for audiobook narration.\n"
        "Requirements:\n"
        "- Keep the same language as the input text.\n"
        "- Preserve all facts, names, numbers, and key details.\n"
        "- Improve listenability with natural spoken rhythm and clear sentence flow.\n"
        "- Prefer concise spoken phrasing and punctuation that supports pauses.\n"
        "- Keep paragraph structure unless a small split improves clarity.\n"
        "- Do not add new information, analysis, or meta commentary.\n"
        "Output only the rewritten text.\n\n"
        "Ahoj svete."
    )


def test_rewriter_cache_is_isolated_by_normalized_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rewrite cache entries should separate by level and share case variants."""

    calls = _install_recording_chat(monkeypatch)
    rewriter = AudioRewriter(model="gpt-4.1-mini", provider_id="openai", api_key="key")

    first = rewriter.rewrite(_translation(), proficiency_level="B2")
    second = rewriter.rewrite(_translation(), proficiency_level="b2")
    third = rewriter.rewrite(_translation(), proficiency_level="A0")

    assert len(calls) == 2
    assert first.rewritten_text == "response-1"
    assert second.rewritten_text == "response-1"
    assert third.rewritten_text == "response-2"
    assert "Target CEFR proficiency level B2" in _user_prompt(calls, 0)
    assert "Target CEFR proficiency level A0" in _user_prompt(calls, 1)


def test_rewriter_legacy_cache_and_prompt_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitted level should keep one rewrite prompt shape and one cache entry."""

    calls = _install_recording_chat(monkeypatch)
    rewriter = AudioRewriter(model="gpt-4.1-mini", provider_id="openai", api_key="key")

    first = rewriter.rewrite(_translation())
    second = rewriter.rewrite(_translation())

    assert len(calls) == 1
    assert first.rewritten_text == second.rewritten_text
    assert "CEFR" not in _user_prompt(calls, 0)


def test_deterministic_bypass_accepts_level_and_passes_text_through() -> None:
    """Bypass rewriter should satisfy the interface and preserve translated text."""

    translation = _translation()

    result = DeterministicBypassRewriter().rewrite(translation, proficiency_level="c2")

    assert result.rewritten_text == translation.translated_text
    assert result.provider == "bypass"
    assert result.model == "deterministic-pass-through-v1"


def test_deterministic_bypass_rejects_invalid_level() -> None:
    """Bypass rewriter should share the interface-level validation rule."""

    with pytest.raises(ValueError, match="Unsupported proficiency level"):
        DeterministicBypassRewriter().rewrite(_translation(), proficiency_level="X1")


def test_translator_omitted_and_explicit_none_reuse_preseeded_legacy_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitted and explicit None should hit the legacy entry; a level should not."""

    calls = _install_recording_chat(monkeypatch)
    translator = OpenAITranslator(model="gpt-4.1-mini", provider_id="openai", api_key="key")
    legacy_key = translator.cache.make_key(
        provider="openai",
        model="gpt-4.1-mini",
        operation="translate",
        input_identity={"target_language": "cs", "source_text": "Hello world."},
    )
    translator.cache.set(legacy_key, "legacy-translation")

    omitted = translator.translate(_chunk(), target_language="cs")
    explicit_none = translator.translate(
        _chunk(),
        target_language="cs",
        proficiency_level=None,
    )
    leveled = translator.translate(_chunk(), target_language="cs", proficiency_level="A2")

    assert omitted.translated_text == "legacy-translation"
    assert explicit_none.translated_text == "legacy-translation"
    assert leveled.translated_text == "response-1"
    assert len(calls) == 1
    assert len(translator.cache.entries) == 2
    assert translator.cache.entries[legacy_key] == "legacy-translation"
    assert translator.cache.hits == 2
    assert translator.cache.misses == 1


def test_rewriter_omitted_and_explicit_none_reuse_preseeded_legacy_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitted and explicit None should hit the legacy entry; a level should not."""

    calls = _install_recording_chat(monkeypatch)
    rewriter = AudioRewriter(model="gpt-4.1-mini", provider_id="openai", api_key="key")
    legacy_key = rewriter.cache.make_key(
        provider="openai",
        model="gpt-4.1-mini",
        operation="rewrite",
        input_identity={"translated_text": "Ahoj svete."},
    )
    rewriter.cache.set(legacy_key, "legacy-rewrite")

    omitted = rewriter.rewrite(_translation())
    explicit_none = rewriter.rewrite(_translation(), proficiency_level=None)
    leveled = rewriter.rewrite(_translation(), proficiency_level="A2")

    assert omitted.rewritten_text == "legacy-rewrite"
    assert explicit_none.rewritten_text == "legacy-rewrite"
    assert leveled.rewritten_text == "response-1"
    assert len(calls) == 1
    assert len(rewriter.cache.entries) == 2
    assert rewriter.cache.entries[legacy_key] == "legacy-rewrite"
    assert rewriter.cache.hits == 2
    assert rewriter.cache.misses == 1


@pytest.mark.parametrize("invalid_level", ["D1", "", "   ", "\t\n"])
def test_audio_rewriter_rejects_invalid_levels_without_touching_cache(
    monkeypatch: pytest.MonkeyPatch,
    invalid_level: str,
) -> None:
    """Invalid levels should fail before provider access and leave cache state intact."""

    calls = _install_recording_chat(monkeypatch)
    rewriter = AudioRewriter(model="gpt-4.1-mini", provider_id="openai", api_key="key")
    rewriter.cache.set("existing", "value")
    entries_before = dict(rewriter.cache.entries)
    hits_before = rewriter.cache.hits
    misses_before = rewriter.cache.misses

    with pytest.raises(ValueError, match="Unsupported proficiency level"):
        rewriter.rewrite(_translation(), proficiency_level=invalid_level)

    assert calls == []
    assert rewriter.cache.entries == entries_before
    assert rewriter.cache.hits == hits_before
    assert rewriter.cache.misses == misses_before

"""Unit tests for YAML/environment configuration loader behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from bookvoice.config import ConfigLoader, RuntimeConfigSources


def test_config_loader_from_yaml_loads_valid_config_and_normalizes_values(
    tmp_path: Path,
) -> None:
    """YAML loader should parse valid payloads and normalize typed/blank values."""

    config_path = tmp_path / "bookvoice.yml"
    expected_input_pdf = Path("tests/files/path_only_placeholder.pdf")
    config_path.write_text(
        f"""
input_pdf: " {expected_input_pdf} "
output_dir: " out "
language: " cs "
provider_translator: " openai "
provider_rewriter: " openai "
provider_tts: " openai "
model_translate: " gpt-4.1-mini "
model_rewrite: " gpt-4.1-mini "
model_tts: " gpt-4o-mini-tts "
tts_voice: " echo "
rewrite_bypass: " yes "
api_key: " test-key "
chunk_size_chars: " 2400 "
chapter_selection: " 1,3-4 "
resume: false
extra:
  profile: " nightly "
""".strip(),
        encoding="utf-8",
    )

    config = ConfigLoader.from_yaml(config_path)

    assert config.input_pdf == expected_input_pdf
    assert config.output_dir == Path("out")
    assert config.language == "cs"
    assert config.provider_translator == "openai"
    assert config.provider_rewriter == "openai"
    assert config.provider_tts == "openai"
    assert config.model_translate == "gpt-4.1-mini"
    assert config.model_rewrite == "gpt-4.1-mini"
    assert config.model_tts == "gpt-4o-mini-tts"
    assert config.tts_voice == "echo"
    assert config.rewrite_bypass is True
    assert config.api_key == "test-key"
    assert config.chunk_size_chars == 2400
    assert config.chapter_selection == "1,3-4"
    assert config.resume is False
    assert config.extra == {"profile": "nightly"}


def test_config_loader_from_yaml_rejects_missing_and_unknown_keys(tmp_path: Path) -> None:
    """YAML loader should fail clearly on missing required or unknown fields."""

    missing_path = tmp_path / "missing.yml"
    missing_path.write_text("output_dir: out\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"missing required key\(s\): input_pdf"):
        ConfigLoader.from_yaml(missing_path)

    unknown_path = tmp_path / "unknown.yml"
    unknown_path.write_text(
        """
input_pdf: in.pdf
output_dir: out
unknown_field: x
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"unsupported key\(s\): unknown_field"):
        ConfigLoader.from_yaml(unknown_path)


def test_config_loader_from_yaml_rejects_invalid_typed_values(tmp_path: Path) -> None:
    """YAML loader should reject invalid typed tokens with actionable errors."""

    invalid_bool_path = tmp_path / "invalid-bool.yml"
    invalid_bool_path.write_text(
        """
input_pdf: in.pdf
output_dir: out
rewrite_bypass: maybe
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="`rewrite_bypass` must be a boolean"):
        ConfigLoader.from_yaml(invalid_bool_path)

    invalid_int_path = tmp_path / "invalid-int.yml"
    invalid_int_path.write_text(
        """
input_pdf: in.pdf
output_dir: out
chunk_size_chars: x
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="`chunk_size_chars` must be a positive integer"):
        ConfigLoader.from_yaml(invalid_int_path)


def test_config_loader_from_env_loads_runtime_values_and_normalizes_blanks() -> None:
    """Environment loader should parse runtime keys and normalize blank strings."""

    expected_input_pdf = Path("tests/files/path_only_placeholder.pdf")
    env = {
        "BOOKVOICE_INPUT_PDF": f" {expected_input_pdf} ",
        "BOOKVOICE_OUTPUT_DIR": " out ",
        "BOOKVOICE_PROVIDER_TRANSLATOR": " openai ",
        "BOOKVOICE_PROVIDER_REWRITER": " openai ",
        "BOOKVOICE_PROVIDER_TTS": " openai ",
        "BOOKVOICE_MODEL_TRANSLATE": " env-model-t ",
        "BOOKVOICE_MODEL_REWRITE": " env-model-r ",
        "BOOKVOICE_MODEL_TTS": " env-model-tts ",
        "BOOKVOICE_TTS_VOICE": " alloy ",
        "BOOKVOICE_REWRITE_BYPASS": " true ",
        "BOOKVOICE_CHAPTER_SELECTION": "   ",
        "OPENAI_API_KEY": " env-api-key ",
    }

    config = ConfigLoader.from_env(env)

    assert config.input_pdf == expected_input_pdf
    assert config.output_dir == Path("out")
    assert config.provider_translator == "openai"
    assert config.provider_rewriter == "openai"
    assert config.provider_tts == "openai"
    assert config.model_translate == "env-model-t"
    assert config.model_rewrite == "env-model-r"
    assert config.model_tts == "env-model-tts"
    assert config.tts_voice == "alloy"
    assert config.rewrite_bypass is True
    assert config.chapter_selection is None
    assert config.api_key == "env-api-key"


def test_config_loader_from_env_preserves_runtime_precedence() -> None:
    """Loaded env config should still resolve runtime values as CLI > secure > env > defaults."""

    config = ConfigLoader.from_env(
        {
            "BOOKVOICE_INPUT_PDF": "in.pdf",
            "BOOKVOICE_MODEL_TRANSLATE": "env-model-t",
            "BOOKVOICE_REWRITE_BYPASS": "false",
            "OPENAI_API_KEY": "env-api-key",
        }
    )

    runtime = config.resolved_provider_runtime(
        RuntimeConfigSources(
            cli={"model_translate": "cli-model-t", "rewrite_bypass": "true"},
            secure={"api_key": "secure-api-key"},
            env=config.runtime_sources.env,
        )
    )

    assert runtime.translate_model == "cli-model-t"
    assert runtime.rewrite_bypass is True
    assert runtime.api_key == "secure-api-key"


def test_config_loader_from_env_rejects_invalid_boolean() -> None:
    """Environment loader should fail clearly for invalid boolean values."""

    with pytest.raises(ValueError, match="`BOOKVOICE_REWRITE_BYPASS` must be a boolean"):
        ConfigLoader.from_env(
            {
                "BOOKVOICE_INPUT_PDF": "in.pdf",
                "BOOKVOICE_REWRITE_BYPASS": "maybe",
            }
        )

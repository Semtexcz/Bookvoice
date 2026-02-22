"""Unit tests for manifest parsing helpers used by pipeline resume."""

from bookvoice.pipeline.resume import manifest_bool, manifest_string


def test_manifest_string_uses_default_for_blank_values() -> None:
    """Manifest string parsing should fallback to default for blank values."""

    payload: dict[str, object] = {"model_translate": "   "}

    assert manifest_string(payload, "model_translate", "gpt-4.1-mini") == "gpt-4.1-mini"


def test_manifest_bool_accepts_mixed_case_tokens() -> None:
    """Manifest boolean parsing should accept mixed-case true/false tokens."""

    true_payload: dict[str, object] = {"rewrite_bypass": "TrUe"}
    false_payload: dict[str, object] = {"rewrite_bypass": " oFf "}

    assert manifest_bool(true_payload, "rewrite_bypass", False) is True
    assert manifest_bool(false_payload, "rewrite_bypass", True) is False


def test_manifest_bool_uses_default_for_invalid_tokens() -> None:
    """Manifest boolean parsing should fallback for invalid string tokens."""

    payload: dict[str, object] = {"rewrite_bypass": "maybe"}

    assert manifest_bool(payload, "rewrite_bypass", False) is False
    assert manifest_bool(payload, "rewrite_bypass", True) is True

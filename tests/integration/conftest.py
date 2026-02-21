"""Integration-test fixtures for deterministic provider behavior."""

from __future__ import annotations

import pytest

from bookvoice.llm.openai_client import OpenAIChatClient


@pytest.fixture(autouse=True)
def _mock_openai_llm_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock OpenAI LLM calls in integration tests to avoid network/key requirements."""

    def _mock_chat_completion(self, **kwargs: object) -> str:
        """Return deterministic placeholder text for translation and rewrite stages."""

        _ = self
        _ = kwargs
        return "integration-mocked-llm-text"

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _mock_chat_completion)

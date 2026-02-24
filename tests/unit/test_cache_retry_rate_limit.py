"""Unit tests for cache-key hardening, retries, rate limiting, and telemetry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from bookvoice.config import BookvoiceConfig
from bookvoice.llm.cache import ResponseCache
from bookvoice.llm.openai_client import OpenAIChatClient, OpenAIProviderError, OpenAISpeechClient
from bookvoice.llm.rate_limiter import RateLimiter
from bookvoice.models.datatypes import Chunk
from bookvoice.pipeline import BookvoicePipeline


class _MockRequestsResponse:
    """Minimal requests response mock used by retry/rate-limit tests."""

    def __init__(self, *, payload: bytes, status_code: int = 200) -> None:
        """Initialize response with payload bytes and status code."""

        self.content = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise HTTP error when status code indicates failure."""

        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class _RecordingRateLimiter:
    """Rate limiter test double that records acquire keys."""

    def __init__(self) -> None:
        """Initialize recording storage."""

        self.keys: list[str] = []

    def acquire(self, key: str) -> None:
        """Record acquisition keys without sleeping."""

        self.keys.append(key)


def test_response_cache_key_is_deterministic_and_normalized() -> None:
    """Cache key should include provider/model/operation and normalize input identity."""

    key_one = ResponseCache.make_key(
        provider="OpenAI",
        model="gpt-4.1-mini",
        operation="translate",
        input_identity={"source_text": "Hello   world", "target_language": "cs"},
    )
    key_two = ResponseCache.make_key(
        provider="openai",
        model="gpt-4.1-mini",
        operation="translate",
        input_identity={"target_language": "cs", "source_text": "Hello world"},
    )

    assert key_one == key_two
    assert key_one.startswith("response:openai:gpt-4.1-mini:translate:")


def test_response_cache_tracks_hits_and_misses() -> None:
    """Cache get/set should keep hit/miss telemetry counters deterministic."""

    cache = ResponseCache()
    assert cache.get("missing-key") is None
    cache.set("known-key", "value")
    assert cache.get("known-key") == "value"

    assert cache.hits == 1
    assert cache.misses == 1
    assert cache.hit_rate() == 0.5


def test_rate_limiter_enforces_minimum_interval_per_key() -> None:
    """Rate limiter should sleep before repeated calls for the same key."""

    state = {"now": 0.0}
    waits: list[float] = []

    def _clock() -> float:
        """Return mutable fake monotonic clock value."""

        return state["now"]

    def _sleep(seconds: float) -> None:
        """Advance fake time and record requested wait duration."""

        waits.append(seconds)
        state["now"] += seconds

    limiter = RateLimiter(min_interval_seconds=0.5, clock=_clock, sleeper=_sleep)
    limiter.acquire("openai:chat:gpt-4.1-mini")
    limiter.acquire("openai:chat:gpt-4.1-mini")

    assert waits == [0.5]


def test_openai_client_retries_transient_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI client should retry timeout failures within bounded retry budget."""

    calls = {"count": 0}
    sleeps: list[float] = []

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Fail once with timeout and then return success payload."""

        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.Timeout("socket timed out")
        return _MockRequestsResponse(
            payload=json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
        )

    def _fake_sleep(delay: float) -> None:
        """Capture retry backoff duration without waiting."""

        sleeps.append(delay)

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)
    monkeypatch.setattr("bookvoice.llm.openai_client.time.sleep", _fake_sleep)

    client = OpenAIChatClient(
        api_key="key",
        max_retries=2,
        retry_backoff_base_seconds=0.2,
        retry_backoff_max_seconds=1.0,
        rate_limiter=RateLimiter(min_interval_seconds=0.0),
    )

    result = client.chat_completion_text(
        model="gpt-4.1-mini",
        system_prompt="system",
        user_prompt="user",
    )

    assert result == "ok"
    assert calls["count"] == 2
    assert sleeps == [0.2]
    assert client.retry_attempt_count == 1


def test_openai_client_does_not_retry_permanent_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI client should not retry invalid API key failures."""

    calls = {"count": 0}

    def _mock_post(_url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Return a deterministic authentication failure response."""

        calls["count"] += 1
        return _MockRequestsResponse(
            status_code=401,
            payload=b'{"error":{"message":"invalid api key"}}',
        )

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    client = OpenAIChatClient(api_key="key", max_retries=3, rate_limiter=RateLimiter(0.0))
    with pytest.raises(OpenAIProviderError, match="authentication failed"):
        client.chat_completion_text(
            model="gpt-4.1-mini",
            system_prompt="system",
            user_prompt="user",
        )

    assert calls["count"] == 1
    assert client.retry_attempt_count == 0


def test_openai_clients_enforce_rate_limiter_on_chat_and_tts_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI chat and speech clients should acquire rate limit tokens per request."""

    limiter = _RecordingRateLimiter()

    def _mock_post(url: str, **_kwargs: object) -> _MockRequestsResponse:
        """Return deterministic payloads for chat and speech endpoints."""

        if url.endswith("/chat/completions"):
            return _MockRequestsResponse(
                payload=json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode("utf-8")
            )
        return _MockRequestsResponse(payload=b"RIFF")

    monkeypatch.setattr("bookvoice.llm.openai_client.requests.post", _mock_post)

    chat_client = OpenAIChatClient(api_key="key", rate_limiter=limiter)
    speech_client = OpenAISpeechClient(api_key="key", rate_limiter=limiter)

    chat_client.chat_completion_text(
        model="gpt-4.1-mini",
        system_prompt="system",
        user_prompt="user",
    )
    speech_client.synthesize_speech(
        model="gpt-4o-mini-tts",
        voice="alloy",
        text="hello",
    )

    assert "openai:chat:gpt-4.1-mini" in limiter.keys
    assert "openai:tts:gpt-4o-mini-tts" in limiter.keys


def test_pipeline_records_cache_telemetry_for_translate_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline translate stage should report cache hits/misses in telemetry metadata."""

    calls = {"count": 0}

    def _mock_chat_completion(self, **_kwargs: object) -> str:
        """Return deterministic translation and count provider invocations."""

        _ = self
        calls["count"] += 1
        return "Ahoj"

    monkeypatch.setattr(OpenAIChatClient, "chat_completion_text", _mock_chat_completion)

    pipeline = BookvoicePipeline()
    config = BookvoiceConfig(input_pdf=Path("in.pdf"), output_dir=Path("out"), api_key="key")
    chunks = [
        Chunk(chapter_index=1, chunk_index=0, text="Hello world.", char_start=0, char_end=12),
        Chunk(chapter_index=1, chunk_index=1, text="Hello world.", char_start=13, char_end=25),
    ]

    translations = pipeline._translate(chunks, config)
    metadata = pipeline._provider_call_manifest_metadata()

    assert len(translations) == 2
    assert calls["count"] == 1
    assert metadata["provider_cache_hits"] == "1"
    assert metadata["provider_cache_misses"] == "1"
    assert metadata["provider_cache_hit_rate"] == "0.5000"

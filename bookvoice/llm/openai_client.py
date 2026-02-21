"""OpenAI HTTP client utilities for LLM and TTS stages.

Responsibilities:
- Send minimal chat-completions and speech requests to OpenAI's REST API.
- Normalize response extraction for deterministic stage integrations.
- Raise actionable provider exceptions for pipeline-level error mapping.
"""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request


class OpenAIProviderError(RuntimeError):
    """Raised when an OpenAI provider request fails or returns malformed output."""


class _OpenAIBaseClient:
    """Shared OpenAI HTTP settings and helpers used by stage-specific clients."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
    ) -> None:
        """Initialize OpenAI HTTP client settings."""

        self.api_key = api_key.strip() if isinstance(api_key, str) else ""
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _require_api_key(self) -> None:
        """Require API key presence before issuing OpenAI requests."""

        if not self.api_key:
            raise OpenAIProviderError(
                "Missing OpenAI API key. Set `OPENAI_API_KEY`, use `--api-key`, or "
                "`--prompt-api-key`."
            )

    @staticmethod
    def _decode_error_body(exc: error.HTTPError) -> str:
        """Decode an HTTP error body into a short diagnostic string."""

        try:
            payload = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            payload = ""
        if payload:
            return payload
        return "No response body."


class OpenAIChatClient(_OpenAIBaseClient):
    """Minimal stdlib-based OpenAI chat-completions HTTP client."""

    def chat_completion_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        """Return the first assistant text response from a chat-completions request."""

        self._require_api_key()

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self.base_url}/chat/completions"
        http_request = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw_payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = self._decode_error_body(exc)
            raise OpenAIProviderError(
                f"OpenAI request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise OpenAIProviderError(f"OpenAI request transport error: {reason}") from exc
        except TimeoutError as exc:
            raise OpenAIProviderError("OpenAI request timed out.") from exc
        except Exception as exc:
            raise OpenAIProviderError(f"OpenAI request failed: {exc}") from exc

        return self._extract_message_text(raw_payload)

    @staticmethod
    def _extract_message_text(raw_payload: str) -> str:
        """Extract first assistant message text from OpenAI chat-completions JSON payload."""

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError("OpenAI returned invalid JSON payload.") from exc

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenAIProviderError("OpenAI response missing non-empty `choices` list.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise OpenAIProviderError("OpenAI response `choices[0]` is malformed.")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise OpenAIProviderError("OpenAI response missing `choices[0].message` object.")

        content = message.get("content")
        text = OpenAIChatClient._message_content_to_text(content)
        normalized = text.strip()
        if not normalized:
            raise OpenAIProviderError("OpenAI response message content is empty.")
        return normalized

    @staticmethod
    def _message_content_to_text(content: Any) -> str:
        """Convert OpenAI message content variants into a plain text string."""

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "".join(parts)
        return ""


class OpenAISpeechClient(_OpenAIBaseClient):
    """Minimal stdlib-based OpenAI speech HTTP client for TTS synthesis."""

    def synthesize_speech(
        self,
        *,
        model: str,
        voice: str,
        text: str,
        response_format: str = "wav",
        speed: float = 1.0,
    ) -> bytes:
        """Return synthesized audio bytes from OpenAI `/audio/speech`."""

        self._require_api_key()

        payload = {
            "model": model,
            "voice": voice,
            "input": text,
            "response_format": response_format,
            "speed": speed,
        }
        body = json.dumps(payload).encode("utf-8")
        endpoint = f"{self.base_url}/audio/speech"
        http_request = request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                audio_bytes = response.read()
        except error.HTTPError as exc:
            detail = self._decode_error_body(exc)
            raise OpenAIProviderError(
                f"OpenAI request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise OpenAIProviderError(f"OpenAI request transport error: {reason}") from exc
        except TimeoutError as exc:
            raise OpenAIProviderError("OpenAI request timed out.") from exc
        except Exception as exc:
            raise OpenAIProviderError(f"OpenAI request failed: {exc}") from exc

        if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
            raise OpenAIProviderError("OpenAI speech response is empty.")
        return bytes(audio_bytes)

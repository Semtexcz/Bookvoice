"""OpenAI HTTP client utilities for LLM and TTS stages.

Responsibilities:
- Send minimal chat-completions and speech requests to OpenAI's REST API.
- Normalize response extraction for deterministic stage integrations.
- Raise actionable provider exceptions for pipeline-level error mapping.
"""

from __future__ import annotations

import json
import re
import socket
from typing import Any

import requests


class OpenAIProviderError(RuntimeError):
    """Raised when an OpenAI provider request fails or returns malformed output."""

    def __init__(
        self,
        message: str,
        *,
        failure_kind: str = "unknown",
        status_code: int | None = None,
        provider_code: str | None = None,
    ) -> None:
        """Initialize provider error metadata for stage-aware diagnostics."""

        super().__init__(message)
        self.failure_kind = failure_kind
        self.status_code = status_code
        self.provider_code = provider_code


class _OpenAIBaseClient:
    """Shared OpenAI HTTP settings and helpers used by stage-specific clients."""

    _MAX_PROVIDER_MESSAGE_CHARS = 180

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
                "`--prompt-api-key`.",
                failure_kind="invalid_api_key",
            )

    def _execute_json_post_bytes(
        self,
        *,
        endpoint_path: str,
        payload: dict[str, Any],
        require_non_empty_response: bool = False,
        empty_response_message: str = "OpenAI response is empty.",
    ) -> bytes:
        """Execute an OpenAI JSON POST request and map failures consistently."""

        endpoint = f"{self.base_url}{endpoint_path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_bytes = bytes(response.content)
        except requests.HTTPError as exc:
            raise self._http_error_to_provider_error(exc) from exc
        except requests.RequestException as exc:
            failure_kind = self._classify_transport_failure(exc)
            if failure_kind == "timeout":
                detail = "OpenAI request timed out."
            else:
                detail = (
                    "OpenAI request transport error: "
                    f"{self._short_message(str(exc))}"
                )
            raise OpenAIProviderError(detail, failure_kind=failure_kind) from exc
        except TimeoutError as exc:
            raise OpenAIProviderError(
                "OpenAI request timed out.",
                failure_kind="timeout",
            ) from exc
        except Exception as exc:
            raise OpenAIProviderError(
                f"OpenAI request failed: {self._short_message(str(exc))}",
                failure_kind="unknown",
            ) from exc

        if require_non_empty_response and not response_bytes:
            raise OpenAIProviderError(empty_response_message)
        return response_bytes

    def _post_json_bytes(
        self,
        *,
        endpoint_path: str,
        payload: dict[str, Any],
        require_non_empty_response: bool = False,
        empty_response_message: str = "OpenAI response is empty.",
    ) -> bytes:
        """POST JSON payload to OpenAI and return raw response bytes."""

        return self._execute_json_post_bytes(
            endpoint_path=endpoint_path,
            payload=payload,
            require_non_empty_response=require_non_empty_response,
            empty_response_message=empty_response_message,
        )

    @staticmethod
    def _decode_error_body(exc: requests.HTTPError) -> str:
        """Decode an HTTP error body into a best-effort UTF-8 payload string."""

        response = exc.response
        if response is None:
            return ""
        try:
            return bytes(response.content).decode("utf-8", errors="replace").strip()
        except Exception:
            return ""

    @classmethod
    def _redact_sensitive_tokens(cls, text: str) -> str:
        """Redact API-key-like tokens from provider error content."""

        redacted = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[redacted-key]", text)
        redacted = re.sub(
            r"(?i)bearer\s+[A-Za-z0-9._-]{12,}",
            "Bearer [redacted-token]",
            redacted,
        )
        return redacted

    @classmethod
    def _short_message(cls, text: str) -> str:
        """Normalize and cap user-facing provider message length."""

        compact = " ".join(text.split())
        if len(compact) <= cls._MAX_PROVIDER_MESSAGE_CHARS:
            return compact
        return f"{compact[: cls._MAX_PROVIDER_MESSAGE_CHARS - 1]}..."

    @classmethod
    def _extract_provider_message(cls, body: str) -> tuple[str, str | None]:
        """Extract a concise provider-facing message and optional provider error code."""

        if not body:
            return "", None

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return cls._short_message(cls._redact_sensitive_tokens(body)), None

        provider_code: str | None = None
        message: str | None = None
        if isinstance(payload, dict):
            error_payload = payload.get("error")
            if isinstance(error_payload, dict):
                code_value = error_payload.get("code")
                if isinstance(code_value, str) and code_value.strip():
                    provider_code = code_value.strip()
                message_value = error_payload.get("message")
                if isinstance(message_value, str) and message_value.strip():
                    message = message_value.strip()

        if message is None:
            message = body

        return cls._short_message(cls._redact_sensitive_tokens(message)), provider_code

    @staticmethod
    def _classify_http_failure(
        status_code: int,
        provider_message: str,
        provider_code: str | None,
    ) -> str:
        """Classify OpenAI HTTP errors into deterministic diagnostic kinds."""

        message_lower = provider_message.lower()
        normalized_code = provider_code.lower() if provider_code is not None else ""

        if status_code == 401 or "api key" in message_lower:
            return "invalid_api_key"
        if normalized_code == "insufficient_quota" or (
            status_code == 429 and "quota" in message_lower
        ):
            return "insufficient_quota"
        if normalized_code == "model_not_found" or (
            "model" in message_lower
            and any(phrase in message_lower for phrase in ("not found", "does not exist", "invalid"))
        ):
            return "invalid_model"
        if status_code in {408, 504} or "timeout" in message_lower or "timed out" in message_lower:
            return "timeout"
        return "http_error"

    @staticmethod
    def _classify_transport_failure(reason: object) -> str:
        """Classify network-layer failures into deterministic diagnostic kinds."""

        if isinstance(reason, TimeoutError | socket.timeout | requests.Timeout):
            return "timeout"
        return "transport"

    @classmethod
    def _http_error_to_provider_error(cls, exc: requests.HTTPError) -> OpenAIProviderError:
        """Convert HTTP errors into normalized provider exceptions with metadata."""

        status_code = exc.response.status_code if exc.response is not None else 0
        body = cls._decode_error_body(exc)
        provider_message, provider_code = cls._extract_provider_message(body)
        failure_kind = cls._classify_http_failure(status_code, provider_message, provider_code)

        headline = {
            "invalid_api_key": "OpenAI authentication failed",
            "insufficient_quota": "OpenAI quota is insufficient for this request",
            "invalid_model": "OpenAI rejected the selected model",
            "timeout": "OpenAI request timed out",
        }.get(failure_kind, "OpenAI request failed")

        if provider_message:
            detail = f"{headline} (HTTP {status_code}): {provider_message}"
        else:
            detail = f"{headline} (HTTP {status_code})."

        return OpenAIProviderError(
            detail,
            failure_kind=failure_kind,
            status_code=status_code,
            provider_code=provider_code,
        )


class OpenAIChatClient(_OpenAIBaseClient):
    """Minimal requests-based OpenAI chat-completions HTTP client."""

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
        raw_payload = self._post_json_bytes(
            endpoint_path="/chat/completions",
            payload=payload,
        ).decode("utf-8")
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
    """Minimal requests-based OpenAI speech HTTP client for TTS synthesis."""

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
        return self._post_json_bytes(
            endpoint_path="/audio/speech",
            payload=payload,
            require_non_empty_response=True,
            empty_response_message="OpenAI speech response is empty.",
        )

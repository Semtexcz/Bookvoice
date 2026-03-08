"""Minimal local typing stubs for the `requests` package used by Bookvoice."""

from typing import Any, Protocol


class RequestException(Exception): ...


class Timeout(RequestException): ...


class ConnectionError(RequestException): ...


class ResponseLike(Protocol):
    content: bytes
    status_code: int


class HTTPError(RequestException):
    response: ResponseLike | None
    def __init__(
        self,
        *args: object,
        request: object | None = ...,
        response: ResponseLike | None = ...,
    ) -> None: ...


class Response(ResponseLike):
    def raise_for_status(self) -> None: ...


def post(
    url: str,
    *,
    headers: dict[str, str] | None = ...,
    json: Any = ...,
    timeout: float | tuple[float, float] | None = ...,
) -> Response: ...

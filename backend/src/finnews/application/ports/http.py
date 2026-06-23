from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class HttpRequest:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None
    acceptable_content_types: tuple[str, ...] = (
        "application/rss+xml",
        "application/atom+xml",
        "application/xml",
        "text/xml",
        "application/json",
        "text/csv",
        "text/plain",
    )


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes


class BoundedHttpClient(Protocol):
    def get(self, request: HttpRequest) -> HttpResponse: ...
    def post(self, request: HttpRequest) -> HttpResponse: ...

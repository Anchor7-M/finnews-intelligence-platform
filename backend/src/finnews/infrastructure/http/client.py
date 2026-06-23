from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlparse

import httpx

from finnews.application.ports.http import HttpRequest, HttpResponse
from finnews.domain.entities import SourceDefinition
from finnews.domain.enums import SourceErrorCategory


class HttpPolicyError(ValueError):
    def __init__(self, category: SourceErrorCategory, message: str, retry_count: int = 0) -> None:
        super().__init__(message)
        self.category = category
        self.retry_count = retry_count


class BoundedSourceHttpClient:
    def __init__(
        self,
        source: SourceDefinition,
        *,
        transport: httpx.BaseTransport | None = None,
        allow_local_http_for_tests: bool = False,
        sleeper: Callable[[float], None] | None = None,
        resolver: Callable[[str], list[str]] | None = None,
    ) -> None:
        self.source = source
        self.allow_local_http_for_tests = allow_local_http_for_tests
        self.sleeper = sleeper or (lambda _: None)
        self.resolver = resolver or _resolve_host_addresses
        limits = httpx.Limits(max_connections=2, max_keepalive_connections=0)
        timeout = httpx.Timeout(
            connect=source.connect_timeout_seconds,
            read=source.read_timeout_seconds,
            write=source.read_timeout_seconds,
            pool=source.connect_timeout_seconds,
        )
        self.client = httpx.Client(
            follow_redirects=False,
            timeout=timeout,
            limits=limits,
            transport=transport,
            trust_env=False,
        )

    def get(self, request: HttpRequest) -> HttpResponse:
        return self._request("GET", request)

    def post(self, request: HttpRequest) -> HttpResponse:
        return self._request("POST", request)

    def _request(self, method: str, request: HttpRequest) -> HttpResponse:
        url = request.url
        redirects = 0
        headers = {
            "User-Agent": self.source.user_agent,
            "Accept": ", ".join(request.acceptable_content_types),
            **request.headers,
        }
        while True:
            self._validate_url(url)
            try:
                if method == "POST":
                    response = self.client.post(url, headers=headers, content=request.body)
                else:
                    response = self.client.get(url, headers=headers)
            except httpx.TimeoutException as exc:
                raise HttpPolicyError(
                    SourceErrorCategory.TIMEOUT, "source request timed out"
                ) from exc
            except httpx.ConnectError as exc:
                raise HttpPolicyError(
                    SourceErrorCategory.CONNECTION, "source connection failed"
                ) from exc
            except httpx.HTTPError as exc:
                raise HttpPolicyError(SourceErrorCategory.UNKNOWN, "source request failed") from exc
            if response.status_code in {301, 302, 303, 307, 308}:
                redirects += 1
                if redirects > 3:
                    raise HttpPolicyError(SourceErrorCategory.POLICY_BLOCKED, "too many redirects")
                location = response.headers.get("location")
                if not location:
                    raise HttpPolicyError(
                        SourceErrorCategory.POLICY_BLOCKED, "redirect without location"
                    )
                url = str(httpx.URL(url).join(location))
                continue
            content = _bounded_content(response, self.source.max_response_bytes)
            _validate_content_type(response, request.acceptable_content_types)
            return HttpResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers={key.lower(): value for key, value in response.headers.items()},
                content=content,
            )

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" and not (
            self.allow_local_http_for_tests and parsed.scheme == "http"
        ):
            raise HttpPolicyError(SourceErrorCategory.POLICY_BLOCKED, "source URL must use https")
        host = (parsed.hostname or "").lower()
        if not host:
            raise HttpPolicyError(SourceErrorCategory.POLICY_BLOCKED, "source URL missing hostname")
        if host not in self.source.approved_hostnames:
            raise HttpPolicyError(
                SourceErrorCategory.POLICY_BLOCKED, "source host is not allowlisted"
            )
        if not self.allow_local_http_for_tests:
            for address in self.resolver(host):
                if _is_blocked_ip(address):
                    raise HttpPolicyError(
                        SourceErrorCategory.DNS_OR_DESTINATION_BLOCKED,
                        "source destination is private or otherwise blocked",
                    )


def _resolve_host_addresses(host: str) -> list[str]:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return [host]
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HttpPolicyError(
            SourceErrorCategory.DNS_OR_DESTINATION_BLOCKED, "source hostname could not resolve"
        ) from exc
    addresses = sorted({str(info[4][0]) for info in infos})
    if not addresses:
        raise HttpPolicyError(
            SourceErrorCategory.DNS_OR_DESTINATION_BLOCKED, "source hostname resolved no addresses"
        )
    return addresses


def _is_blocked_ip(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
    )


def _bounded_content(response: httpx.Response, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > max_bytes:
            raise HttpPolicyError(
                SourceErrorCategory.OVERSIZED_RESPONSE,
                f"source response exceeded {max_bytes} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_content_type(response: httpx.Response, allowed: tuple[str, ...]) -> None:
    if response.status_code == 304:
        return
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if not content_type:
        raise HttpPolicyError(SourceErrorCategory.CONTENT_TYPE, "missing content-type")
    if content_type not in allowed:
        raise HttpPolicyError(
            SourceErrorCategory.CONTENT_TYPE,
            f"unsupported content-type: {content_type}",
        )

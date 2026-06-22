from __future__ import annotations

import httpx
import pytest

from finnews.application.ports.http import HttpRequest
from finnews.domain.entities import SourceDefinition
from finnews.domain.enums import SourceApprovalStatus, SourceType
from finnews.infrastructure.http.client import BoundedSourceHttpClient, HttpPolicyError


def source(url: str = "https://mock.local/feed.xml", max_bytes: int = 128) -> SourceDefinition:
    return SourceDefinition(
        source_id="mock",
        display_name="Mock",
        source_type=SourceType.RSS,
        approved_hostnames=[
            "mock.local",
            "redirect.local",
            "127.0.0.1",
            "::1",
            "10.0.0.1",
            "fd00::1",
            "169.254.1.1",
        ],
        review_status=SourceApprovalStatus.APPROVED,
        enabled=True,
        base_url=url,
        terms_url="https://mock.local/terms",
        documentation_url="https://mock.local/docs",
        reviewer="test",
        max_response_bytes=max_bytes,
        minimum_interval_seconds=0,
    )


def test_https_and_allowlist_are_enforced() -> None:
    client = BoundedSourceHttpClient(source())
    with pytest.raises(HttpPolicyError, match="https"):
        client.get(HttpRequest("http://mock.local/feed.xml"))
    with pytest.raises(HttpPolicyError, match="allowlisted"):
        client.get(HttpRequest("https://evil.local/feed.xml"))


def test_loopback_blocked_in_live_mode() -> None:
    client = BoundedSourceHttpClient(source("https://127.0.0.1/feed.xml"))
    with pytest.raises(HttpPolicyError, match="private"):
        client.get(HttpRequest("https://127.0.0.1/feed.xml"))


@pytest.mark.parametrize(
    "url",
    [
        "https://[::1]/feed.xml",
        "https://10.0.0.1/feed.xml",
        "https://[fd00::1]/feed.xml",
        "https://169.254.1.1/feed.xml",
    ],
)
def test_literal_blocked_destinations(url: str) -> None:
    client = BoundedSourceHttpClient(source(url))
    with pytest.raises(HttpPolicyError, match="private"):
        client.get(HttpRequest(url))


def test_hostname_resolution_blocks_private_and_mixed_answers() -> None:
    client = BoundedSourceHttpClient(source(), resolver=lambda _: ["93.184.216.34", "10.0.0.2"])
    with pytest.raises(HttpPolicyError, match="private"):
        client.get(HttpRequest("https://mock.local/feed.xml"))


def test_redirect_to_blocked_or_non_allowlisted_destination_is_rejected() -> None:
    blocked = BoundedSourceHttpClient(
        source(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(302, headers={"location": "https://127.0.0.1/feed.xml"})
        ),
        resolver=lambda host: [host],
    )
    with pytest.raises(HttpPolicyError, match="private"):
        blocked.get(HttpRequest("https://mock.local/feed.xml"))

    non_allowlisted = BoundedSourceHttpClient(
        source(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(302, headers={"location": "https://evil.local/feed.xml"})
        ),
        resolver=lambda _: ["93.184.216.34"],
    )
    with pytest.raises(HttpPolicyError, match="allowlisted"):
        non_allowlisted.get(HttpRequest("https://mock.local/feed.xml"))


def test_excessive_redirect_chain_is_rejected() -> None:
    client = BoundedSourceHttpClient(
        source(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(302, headers={"location": "https://mock.local/feed.xml"})
        ),
        resolver=lambda _: ["93.184.216.34"],
    )
    with pytest.raises(HttpPolicyError, match="too many redirects"):
        client.get(HttpRequest("https://mock.local/feed.xml"))


def test_redirect_revalidated_and_content_type_checked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "mock.local":
            return httpx.Response(302, headers={"location": "https://redirect.local/feed.xml"})
        return httpx.Response(
            200,
            headers={"content-type": "application/rss+xml"},
            content=b"<rss><channel></channel></rss>",
        )

    client = BoundedSourceHttpClient(
        source(), transport=httpx.MockTransport(handler), resolver=lambda _: ["93.184.216.34"]
    )
    response = client.get(HttpRequest("https://mock.local/feed.xml"))
    assert response.status_code == 200
    assert response.url == "https://redirect.local/feed.xml"


def test_oversized_and_invalid_content_type_are_rejected() -> None:
    oversized = BoundedSourceHttpClient(
        source(max_bytes=4),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, headers={"content-type": "application/rss+xml"}, content=b"12345"
            )
        ),
        resolver=lambda _: ["93.184.216.34"],
    )
    with pytest.raises(HttpPolicyError, match="exceeded"):
        oversized.get(HttpRequest("https://mock.local/feed.xml"))

    invalid = BoundedSourceHttpClient(
        source(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, headers={"content-type": "text/html"}, content=b"x")
        ),
        resolver=lambda _: ["93.184.216.34"],
    )
    with pytest.raises(HttpPolicyError, match="content-type"):
        invalid.get(HttpRequest("https://mock.local/feed.xml"))


def test_response_size_edge_cases_and_proxy_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    exact = BoundedSourceHttpClient(
        source(max_bytes=5),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                headers={"content-type": "application/rss+xml", "content-length": "1"},
                content=b"12345",
            )
        ),
        resolver=lambda _: ["93.184.216.34"],
    )
    assert exact.get(HttpRequest("https://mock.local/feed.xml")).content == b"12345"

    above = BoundedSourceHttpClient(
        source(max_bytes=5),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, headers={"content-type": "application/rss+xml"}, content=b"123456"
            )
        ),
        resolver=lambda _: ["93.184.216.34"],
    )
    with pytest.raises(HttpPolicyError, match="exceeded"):
        above.get(HttpRequest("https://mock.local/feed.xml"))

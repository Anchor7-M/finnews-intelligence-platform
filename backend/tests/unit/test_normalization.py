from __future__ import annotations

from datetime import UTC

import pytest

from finnews.infrastructure.normalization import (
    comparison_text,
    market_date,
    normalize_display_text,
    normalize_url,
    parse_timestamp,
    validate_language,
)


def test_nfkc_whitespace_and_comparison() -> None:
    assert normalize_display_text("ＡＬＰ\n  results") == "ALP results"
    assert comparison_text(" BrightRiver  CLOUD ") == "brightriver cloud"


def test_url_tracking_parameter_removal() -> None:
    assert (
        normalize_url("https://Example.com/a?utm_source=x&id=1#frag")
        == "https://example.com/a?id=1"
    )


def test_timezone_normalization_and_market_date() -> None:
    parsed = parse_timestamp("2026-06-20T09:10:00+08:00")
    assert parsed.tzinfo == UTC
    assert market_date(parsed, "Asia/Shanghai").isoformat() == "2026-06-20"


def test_invalid_language_rejected() -> None:
    with pytest.raises(ValueError):
        validate_language("xx")

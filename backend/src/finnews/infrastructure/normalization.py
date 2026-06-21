from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, date, datetime
from typing import cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from dateutil import parser

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}

VALID_LANGUAGES = {"en", "zh"}


def normalize_display_text(value: str, max_length: int = 500) -> str:
    text = unicodedata.normalize("NFKC", value)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length]


def comparison_text(value: str) -> str:
    return normalize_display_text(value).lower()


def validate_language(value: str) -> str:
    lang = value.strip().lower()
    if lang not in VALID_LANGUAGES:
        raise ValueError(f"unsupported language: {value}")
    return lang


def parse_timestamp(value: str) -> datetime:
    parsed = cast(datetime, parser.parse(value))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def market_date(value: datetime, timezone_name: str) -> date:
    return value.astimezone(ZoneInfo(timezone_name)).date()


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("url must be absolute http(s)")
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    normalized = parts._replace(
        scheme=parts.scheme.lower(),
        netloc=parts.netloc.lower(),
        query=urlencode(query, doseq=True),
        fragment="",
    )
    return urlunsplit(normalized)


def deterministic_hash(*parts: str) -> str:
    payload = "\n".join(comparison_text(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

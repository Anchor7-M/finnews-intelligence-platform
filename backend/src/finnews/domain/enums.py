from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    FIXTURE = "fixture"
    RSS = "rss"
    ATOM = "atom"
    IMPORT = "import"
    OFFICIAL_ANNOUNCEMENT = "official_announcement"
    OTHER = "other"


class IngestionPolicy(StrEnum):
    METADATA_ONLY = "metadata_only"
    DISABLED = "disabled"


class RunStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingState(StrEnum):
    RAW = "raw"
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"


class DuplicateType(StrEnum):
    EXACT = "exact"
    NEAR = "near"


class EventType(StrEnum):
    EARNINGS = "earnings"
    MERGER_ACQUISITION = "merger_acquisition"
    POLICY_REGULATION = "policy_regulation"
    OPERATIONS_PRODUCT = "operations_product"
    FINANCING_CAPITAL = "financing_capital"
    LITIGATION_PENALTY = "litigation_penalty"
    GOVERNANCE_PERSONNEL = "governance_personnel"
    MACRO_MARKET = "macro_market"
    OTHER = "other"


class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNCERTAIN = "uncertain"

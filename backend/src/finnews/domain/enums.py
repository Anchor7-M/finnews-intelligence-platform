from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    FIXTURE = "fixture"
    RSS = "rss"
    ATOM = "atom"
    DOCUMENTED_JSON_API = "documented_json_api"
    USER_EXPORT_JSON = "user_export_json"
    USER_EXPORT_CSV = "user_export_csv"
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


class SourceApprovalStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class SourceHealthStatus(StrEnum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DISABLED = "disabled"
    BLOCKED = "blocked"


class FetchOutcome(StrEnum):
    SUCCESS = "success"
    NO_CHANGE = "no_change"
    DRY_RUN = "dry_run"
    POLICY_BLOCKED = "policy_blocked"
    RATE_LIMITED = "rate_limited"
    FAILED = "failed"


class SourceErrorCategory(StrEnum):
    NONE = "none"
    POLICY_BLOCKED = "policy_blocked"
    DNS_OR_DESTINATION_BLOCKED = "dns_or_destination_blocked"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    RATE_LIMITED = "rate_limited"
    TRANSIENT_HTTP = "transient_http"
    PERMANENT_HTTP = "permanent_http"
    OVERSIZED_RESPONSE = "oversized_response"
    CONTENT_TYPE = "content_type"
    PARSE = "parse"
    VALIDATION = "validation"
    PERSISTENCE = "persistence"
    UNKNOWN = "unknown"

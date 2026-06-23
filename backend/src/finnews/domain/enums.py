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


class AssetClass(StrEnum):
    US_EQUITY = "us_equity"
    ETF = "etf"
    EQUITY_INDEX = "equity_index"
    FX = "fx"
    PRECIOUS_METAL = "precious_metal"
    COMMODITY = "commodity"
    FUTURES_ROOT = "futures_root"
    FUTURES_CONTRACT = "futures_contract"
    CRYPTO_ASSET = "crypto_asset"
    MACRO_INDICATOR = "macro_indicator"
    INTEREST_RATE = "interest_rate"


class AssetStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SymbolNamespace(StrEnum):
    CANONICAL = "canonical"
    NEWS_SOURCE = "news_source"
    SEC_CIK_OR_ISSUER = "sec_cik_or_issuer"
    MARKET_DATA = "market_data"
    RESEARCH = "research"
    MT5_BROKER_LOCAL = "mt5_broker_local"


class CrossAssetEventFamily(StrEnum):
    MONETARY_POLICY = "monetary_policy"
    INFLATION = "inflation"
    LABOR_MARKET = "labor_market"
    ECONOMIC_GROWTH = "economic_growth"
    LIQUIDITY_FUNDING = "liquidity_funding"
    FISCAL_POLICY = "fiscal_policy"
    REGULATION_ENFORCEMENT = "regulation_enforcement"
    CORPORATE_EARNINGS_GUIDANCE = "corporate_earnings_guidance"
    MERGERS_CORPORATE_ACTIONS = "mergers_corporate_actions"
    COMMODITY_SUPPLY = "commodity_supply"
    INVENTORY_DEMAND = "inventory_demand"
    GEOPOLITICAL_RISK = "geopolitical_risk"
    DERIVATIVES_POSITIONING = "derivatives_positioning"
    EXCHANGE_MARKET_INFRASTRUCTURE = "exchange_market_infrastructure"
    CRYPTO_PROTOCOL_ECOSYSTEM = "crypto_protocol_ecosystem"
    CRYPTO_REGULATION = "crypto_regulation"
    IDIOSYNCRATIC_COMPANY_EVENT = "idiosyncratic_company_event"
    OTHER_UNCERTAIN = "other_uncertain"


class ImpactDirection(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


class ImpactHorizon(StrEnum):
    INTRADAY = "intraday"
    ONE_DAY = "one_day"
    ONE_WEEK = "one_week"
    ONE_MONTH = "one_month"


class ImpactRelationshipType(StrEnum):
    DIRECT_ISSUER = "direct_issuer"
    SECTOR_INDUSTRY = "sector_industry"
    INDEX_CONSTITUENT = "index_constituent"
    CURRENCY_TRANSLATION = "currency_translation"
    RATE_SENSITIVITY = "rate_sensitivity"
    INFLATION_SENSITIVITY = "inflation_sensitivity"
    SAFE_HAVEN_HYPOTHESIS = "safe_haven_hypothesis"
    COMMODITY_INPUT_EXPOSURE = "commodity_input_exposure"
    RISK_SENTIMENT_HYPOTHESIS = "risk_sentiment_hypothesis"
    REGULATORY_EXPOSURE = "regulatory_exposure"
    CORRELATION_HYPOTHESIS = "correlation_hypothesis"
    UNCERTAIN_OTHER = "uncertain_other"


class ResearchSignalStatus(StrEnum):
    INFORMATIONAL = "informational"
    RESEARCH = "research"
    ABSTAINED = "abstained"
    REJECTED = "rejected"
    EXPIRED = "expired"


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

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from finnews.domain.entities import SourceDefinition, SourceRetryPolicy
from finnews.domain.enums import IngestionPolicy, SourceApprovalStatus, SourceType

MAX_M1A_RESPONSE_BYTES = 5_000_000
DEFAULT_SOURCE_CONFIG_DIR = Path(__file__).resolve().parents[5] / "config" / "sources"
DEFAULT_SOURCE_LOCAL_OVERRIDE = (
    Path(__file__).resolve().parents[5] / "config" / "sources.local.yaml"
)
SECRET_KEY_FRAGMENTS = ("secret", "password", "token", "api_key", "apikey", "credential")


class SourceConfigError(ValueError):
    pass


class RetryPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_retries: int = Field(default=2, ge=0, le=2)
    base_delay_seconds: float = Field(default=1.0, ge=0.0, le=30.0)
    max_delay_seconds: float = Field(default=30.0, ge=0.0, le=30.0)


class SourceDefinitionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    display_name: str = Field(min_length=1, max_length=240)
    source_type: SourceType
    approved_hostnames: list[str] = Field(default_factory=list)
    review_status: SourceApprovalStatus = SourceApprovalStatus.UNREVIEWED
    enabled: bool = False
    base_url: str | None = None
    import_format: str | None = None
    terms_url: str
    documentation_url: str | None = None
    reviewed_date: str | None = None
    reviewer: str | None = None
    content_storage_policy: IngestionPolicy = IngestionPolicy.METADATA_ONLY
    provenance_required: bool = True
    language: str = Field(default="en", min_length=2, max_length=16)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    connect_timeout_seconds: float = Field(default=5.0, ge=0.1, le=30.0)
    read_timeout_seconds: float = Field(default=15.0, ge=0.1, le=30.0)
    max_response_bytes: int = Field(default=2_000_000, ge=1, le=MAX_M1A_RESPONSE_BYTES)
    retry_policy: RetryPolicyConfig = Field(default_factory=RetryPolicyConfig)
    minimum_interval_seconds: int = Field(default=3600, ge=0)
    cursor_strategy: str | None = None
    field_mapping: dict[str, str] = Field(default_factory=dict)
    user_agent: str = Field(default="finnews-intelligence-platform/0.1 (+local research)")
    notes: str = ""
    risk_classification: str = Field(default="medium", pattern=r"^(low|medium|high)$")
    review_evidence_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    source_config_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    endpoint_template: str | None = None
    parameter_schema: dict[str, str] = Field(default_factory=dict)
    user_agent_env_var: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]*$")
    user_agent_template: str | None = None
    max_items_per_smoke: int = Field(default=5, ge=1, le=5)

    @field_validator("terms_url", "documentation_url", "base_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlparse(value)
        if parsed.scheme != "https":
            raise ValueError("URL must use https")
        if not parsed.netloc:
            raise ValueError("URL must include a hostname")
        return value

    @field_validator("endpoint_template")
    @classmethod
    def validate_endpoint_template(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("endpoint_template must be an absolute https URL")
        return value

    @field_validator("approved_hostnames")
    @classmethod
    def normalize_hosts(cls, value: list[str]) -> list[str]:
        return [host.strip().lower() for host in value if host.strip()]

    @model_validator(mode="after")
    def validate_source_rules(self) -> SourceDefinitionConfig:
        if self.content_storage_policy is not IngestionPolicy.METADATA_ONLY:
            raise ValueError("Milestone 1A supports metadata_only storage only")
        if self.source_type in {SourceType.RSS, SourceType.ATOM, SourceType.DOCUMENTED_JSON_API}:
            if not self.base_url:
                raise ValueError("network sources require base_url")
            host = urlparse(self.base_url).hostname or ""
            if host.lower() not in self.approved_hostnames:
                raise ValueError("base_url host must be listed in approved_hostnames")
            if self.endpoint_template:
                endpoint_host = urlparse(self.endpoint_template).hostname or ""
                if endpoint_host.lower() not in self.approved_hostnames:
                    raise ValueError("endpoint_template host must be listed in approved_hostnames")
            if not self.documentation_url:
                raise ValueError("network sources require documentation_url")
        if self.source_type in {SourceType.USER_EXPORT_JSON, SourceType.USER_EXPORT_CSV}:
            if self.base_url:
                raise ValueError("user export sources must not define base_url")
            expected = "json" if self.source_type is SourceType.USER_EXPORT_JSON else "csv"
            if self.import_format != expected:
                raise ValueError(f"{self.source_type.value} requires import_format={expected}")
        if self.enabled and self.review_status is not SourceApprovalStatus.APPROVED:
            raise ValueError("enabled sources must be approved")
        if self.review_status is SourceApprovalStatus.APPROVED and not self.reviewer:
            raise ValueError("approved sources require reviewer metadata")
        return self

    def to_domain(self) -> SourceDefinition:
        retry = SourceRetryPolicy(
            max_retries=self.retry_policy.max_retries,
            base_delay_seconds=self.retry_policy.base_delay_seconds,
            max_delay_seconds=self.retry_policy.max_delay_seconds,
        )
        return SourceDefinition(
            source_id=self.source_id,
            display_name=self.display_name,
            source_type=self.source_type,
            approved_hostnames=list(self.approved_hostnames),
            review_status=self.review_status,
            enabled=self.enabled,
            base_url=self.base_url,
            import_format=self.import_format,
            terms_url=self.terms_url,
            documentation_url=self.documentation_url,
            reviewed_date=self.reviewed_date,
            reviewer=self.reviewer,
            content_storage_policy=self.content_storage_policy,
            provenance_required=self.provenance_required,
            language=self.language,
            timezone=self.timezone,
            connect_timeout_seconds=self.connect_timeout_seconds,
            read_timeout_seconds=self.read_timeout_seconds,
            max_response_bytes=self.max_response_bytes,
            retry_policy=retry,
            minimum_interval_seconds=self.minimum_interval_seconds,
            cursor_strategy=self.cursor_strategy,
            field_mapping=dict(self.field_mapping),
            user_agent=self.user_agent,
            notes=self.notes,
            risk_classification=self.risk_classification,
            review_evidence_id=self.review_evidence_id,
            source_config_sha256=self.source_config_sha256,
            endpoint_template=self.endpoint_template,
            parameter_schema=dict(self.parameter_schema),
            user_agent_env_var=self.user_agent_env_var,
            user_agent_template=self.user_agent_template,
            max_items_per_smoke=self.max_items_per_smoke,
        )


class SourceOverrideItemConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    enabled: bool


class SourceOverrideConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[SourceOverrideItemConfig] = Field(default_factory=list)


def load_source_definitions(config_dir: Path | None = None) -> list[SourceDefinition]:
    config_dir = config_dir or Path(
        os.environ.get("FINNEWS_SOURCE_CONFIG_DIR", str(DEFAULT_SOURCE_CONFIG_DIR))
    )
    if not config_dir.exists():
        return []
    definitions: list[SourceDefinition] = []
    seen: set[str] = set()
    for path in sorted(config_dir.glob("*.yaml")):
        data = _read_yaml(path)
        _reject_secret_like_fields(data, path)
        items = data.get("sources")
        if not isinstance(items, list):
            raise SourceConfigError(f"{path}: expected top-level 'sources' list")
        for index, item in enumerate(items, start=1):
            try:
                config = SourceDefinitionConfig.model_validate(item)
            except ValidationError as exc:
                raise SourceConfigError(f"{path}: source #{index} invalid: {exc}") from exc
            if config.source_id in seen:
                raise SourceConfigError(f"duplicate source_id: {config.source_id}")
            seen.add(config.source_id)
            definitions.append(config.to_domain())
    if os.environ.get("FINNEWS_SOURCE_LOCAL_OVERRIDE"):
        return _apply_local_overrides(definitions)
    return definitions


def validate_source_definitions(config_dir: Path | None = None) -> list[str]:
    return [definition.source_id for definition in load_source_definitions(config_dir)]


def load_enabled_local_override_source_ids(path: Path | None = None) -> set[str]:
    override_path = path or Path(
        os.environ.get("FINNEWS_SOURCE_LOCAL_OVERRIDE", str(DEFAULT_SOURCE_LOCAL_OVERRIDE))
    )
    if not override_path.exists():
        return set()
    data = _read_yaml(override_path)
    _reject_secret_like_fields(data, override_path)
    try:
        overrides = SourceOverrideConfig.model_validate(data)
    except ValidationError as exc:
        raise SourceConfigError(f"{override_path}: source override invalid: {exc}") from exc
    return {item.source_id for item in overrides.sources if item.enabled}


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise SourceConfigError(f"{path}: source config must be UTF-8") from exc
    except yaml.YAMLError as exc:
        raise SourceConfigError(f"{path}: malformed YAML") from exc
    if not isinstance(raw, dict):
        raise SourceConfigError(f"{path}: expected YAML mapping")
    return raw


def _apply_local_overrides(definitions: list[SourceDefinition]) -> list[SourceDefinition]:
    override_path = Path(
        os.environ.get("FINNEWS_SOURCE_LOCAL_OVERRIDE", str(DEFAULT_SOURCE_LOCAL_OVERRIDE))
    )
    if not override_path.exists():
        return definitions
    data = _read_yaml(override_path)
    _reject_secret_like_fields(data, override_path)
    try:
        overrides = SourceOverrideConfig.model_validate(data)
    except ValidationError as exc:
        raise SourceConfigError(f"{override_path}: source override invalid: {exc}") from exc
    by_id = {definition.source_id: definition for definition in definitions}
    seen: set[str] = set()
    for item in overrides.sources:
        if item.source_id in seen:
            raise SourceConfigError(
                f"{override_path}: duplicate override source_id: {item.source_id}"
            )
        seen.add(item.source_id)
        if item.source_id not in by_id:
            raise SourceConfigError(
                f"{override_path}: unknown override source_id: {item.source_id}"
            )
        current = by_id[item.source_id]
        if item.enabled and current.review_status is not SourceApprovalStatus.APPROVED:
            raise SourceConfigError(
                f"{override_path}: cannot enable unapproved source: {item.source_id}"
            )
        by_id[item.source_id] = replace(current, enabled=item.enabled)
    return [by_id[definition.source_id] for definition in definitions]


def _reject_secret_like_fields(value: object, path: Path, trail: str = "") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key).lower()
            nested_trail = f"{trail}.{key}" if trail else str(key)
            if any(fragment in key_text for fragment in SECRET_KEY_FRAGMENTS):
                raise SourceConfigError(f"{path}: secret-like field is not allowed: {nested_trail}")
            _reject_secret_like_fields(nested, path, nested_trail)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_secret_like_fields(nested, path, f"{trail}[{index}]")

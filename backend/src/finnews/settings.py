from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FINNEWS_", env_file=".env", extra="ignore")

    env: str = "development"
    profile: str = "memory"
    database_url: str = "postgresql+psycopg://finnews:finnews@127.0.0.1:55432/finnews"
    log_level: str = "INFO"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    market_timezone: str = "Asia/Shanghai"
    near_duplicate_threshold: float = Field(default=0.86, ge=0.0, le=1.0)
    near_duplicate_window_hours: int = Field(default=72, ge=1, le=24 * 30)
    near_duplicate_max_candidates: int = Field(default=200, ge=1, le=1000)
    max_fixture_bytes: int = 5_000_000

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 16_384

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 16_384

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    debug: bool = False

    auth_token: str = ""

    allowed_origins: str = "*"

    database_url: str = "sqlite+aiosqlite:///./data/fast_code.db"
    data_dir: Path = Path("data")

    src_root: str = ""

    max_sessions: int = 10
    work_dir: str = ""

    rate_limit_rpm: int = 60

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()

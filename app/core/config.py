"""Application configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings loaded from environment variables and a local .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(min_length=1)
    app_env: str = Field(min_length=1)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = Field(min_length=1)
    documents_path: Path = Field(default=Path("data/documents"), validate_default=True)

    @field_validator("documents_path")
    @classmethod
    def validate_documents_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            project_root = Path(__file__).resolve().parents[2]
            value = project_root / value
        if value.exists() and not value.is_dir():
            raise ValueError("DOCUMENTS_PATH must point to a directory")
        value.mkdir(parents=True, exist_ok=True)
        return value.resolve()

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use the postgresql+psycopg scheme")
        return value


def load_settings() -> Settings:
    """Load and validate application settings."""
    return Settings()

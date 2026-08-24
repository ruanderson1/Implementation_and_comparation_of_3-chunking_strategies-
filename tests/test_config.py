from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_valid_values() -> None:
    settings = Settings(
        _env_file=None,
        app_name="Education RAG",
        app_env="test",
        log_level="INFO",
        database_url="postgresql+psycopg://user:password@localhost:5432/education_rag",
    )

    assert settings.app_name == "Education RAG"


def test_settings_reject_invalid_database_scheme() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_name="Education RAG",
            app_env="test",
            database_url="sqlite:///education_rag.db",
        )

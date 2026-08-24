from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import OperationalError

from app.core.database import (
    DatabaseConnectionError,
    PgvectorUnavailableError,
    check_database_connection,
    enable_pgvector,
)


def test_check_database_connection_runs_simple_query() -> None:
    engine = MagicMock()

    check_database_connection(engine)

    engine.connect.return_value.__enter__.return_value.execute.assert_called_once()


def test_check_database_connection_hides_connection_details() -> None:
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("connection refused for postgres://user:secret@host")
    )

    with pytest.raises(DatabaseConnectionError, match="PostgreSQL is unavailable"):
        check_database_connection(engine)


def test_enable_pgvector_creates_and_confirms_extension() -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one_or_none.return_value = "vector"

    enable_pgvector(engine)

    assert connection.execute.call_count == 2


def test_enable_pgvector_fails_when_extension_is_missing() -> None:
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(PgvectorUnavailableError, match="pgvector is not available"):
        enable_pgvector(engine)

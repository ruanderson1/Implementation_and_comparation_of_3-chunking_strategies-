"""Synchronous PostgreSQL and pgvector helpers."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

from app.core.config import Settings


class DatabaseConnectionError(RuntimeError):
    """Raised when PostgreSQL cannot be reached."""


class DatabaseAuthenticationError(DatabaseConnectionError):
    """Raised when PostgreSQL rejects the supplied credentials."""


class PgvectorUnavailableError(RuntimeError):
    """Raised when pgvector cannot be enabled or verified."""


def create_database_engine(settings: Settings) -> Engine:
    """Create a synchronous SQLAlchemy engine for the configured database."""
    return create_engine(settings.database_url, pool_pre_ping=True)


def check_database_connection(engine: Engine) -> None:
    """Verify that PostgreSQL accepts a simple query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as error:
        _raise_connection_error(error)
    except DBAPIError as error:
        _raise_connection_error(error)
    except SQLAlchemyError as error:
        raise DatabaseConnectionError("Unable to connect to PostgreSQL.") from error


def enable_pgvector(engine: Engine) -> None:
    """Enable pgvector and confirm that PostgreSQL reports it as installed."""
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            extension_name = connection.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one_or_none()
    except SQLAlchemyError as error:
        raise PgvectorUnavailableError("pgvector could not be enabled.") from error

    if extension_name != "vector":
        raise PgvectorUnavailableError("pgvector is not available in this PostgreSQL instance.")


def dispose_database_engine(engine: Engine) -> None:
    """Release database connections held by an engine."""
    engine.dispose()


def _raise_connection_error(error: BaseException) -> None:
    message = str(error).lower()
    if "authentication" in message or "password" in message:
        raise DatabaseAuthenticationError("PostgreSQL authentication was refused.") from error
    raise DatabaseConnectionError("PostgreSQL is unavailable.") from error

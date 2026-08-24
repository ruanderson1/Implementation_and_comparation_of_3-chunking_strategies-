"""CLI entry point for Education RAG."""

from __future__ import annotations

import logging
import sys

from pydantic import ValidationError
from sqlalchemy import Engine

from app.core.config import load_settings
from app.core.database import (
    DatabaseAuthenticationError,
    DatabaseConnectionError,
    PgvectorUnavailableError,
    check_database_connection,
    create_database_engine,
    dispose_database_engine,
    enable_pgvector,
)
from app.rag.ingestion import load_documents

logger = logging.getLogger(__name__)


def run() -> int:
    """Run the initial CLI startup checks and return a process exit code."""
    engine: Engine | None = None

    try:
        settings = load_settings()
        print(settings.app_name)
        print("Configuration loaded")

        engine = create_database_engine(settings)
        check_database_connection(engine)
        print("PostgreSQL connected")

        enable_pgvector(engine)
        print("pgvector extension available")
        print("\nVerificando documentos...")
        try:
            results = load_documents(settings.documents_path)
        except OSError:
            logger.exception("Unable to inspect the configured documents directory")
            print("Aviso: não foi possível acessar o diretório configurado em DOCUMENTS_PATH.")
            return 0
        if not results:
            print("Aviso: nenhum PDF encontrado no diretório configurado em DOCUMENTS_PATH.")
        else:
            print(f"{len(results)} PDFs encontrados")
            for result in results:
                if result.failures:
                    print(
                        f"Falha ao ler {result.info.source}; consulte os logs de desenvolvimento."
                    )
                else:
                    print(
                        f"{result.info.source}: {result.total_pages} páginas, "
                        f"{result.text_pages} com texto"
                    )
                for warning in result.warnings:
                    print(f"Aviso: {warning}")
            print(f"\nDocumentos carregados: {sum(not r.failures for r in results)}")
            print(f"Páginas carregadas: {sum(len(r.pages) for r in results)}")
            print(f"Páginas sem texto: {sum(len(r.empty_pages) for r in results)}")
        return 0
    except ValidationError:
        print("Configuration error: review the required environment variables.", file=sys.stderr)
        return 1
    except DatabaseAuthenticationError:
        print("Database error: PostgreSQL authentication was refused.", file=sys.stderr)
        return 1
    except DatabaseConnectionError:
        print("Database error: PostgreSQL is unavailable.", file=sys.stderr)
        return 1
    except PgvectorUnavailableError:
        print("Database error: pgvector is unavailable.", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            dispose_database_engine(engine)


if __name__ == "__main__":
    raise SystemExit(run())

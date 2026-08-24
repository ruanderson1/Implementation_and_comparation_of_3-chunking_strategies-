from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.documents import Document

from app.core.config import Settings
from app.core.database import DatabaseConnectionError
from app.main import run
from app.rag.ingestion import DocumentInfo, PDFLoadResult


def test_run_reports_success(monkeypatch, capsys) -> None:
    settings = Settings(
        _env_file=None,
        app_name="Education RAG",
        app_env="test",
        database_url="postgresql+psycopg://user:password@localhost:5432/education_rag",
    )
    engine = MagicMock()
    monkeypatch.setattr("app.main.load_settings", lambda: settings)
    monkeypatch.setattr("app.main.create_database_engine", lambda _: engine)
    monkeypatch.setattr("app.main.check_database_connection", lambda _: None)
    monkeypatch.setattr("app.main.enable_pgvector", lambda _: None)
    monkeypatch.setattr("app.main.load_documents", lambda _: [])

    assert run() == 0
    assert "PostgreSQL connected" in capsys.readouterr().out
    engine.dispose.assert_called_once()


def test_run_reports_sanitized_database_failure(monkeypatch, capsys) -> None:
    settings = Settings(
        _env_file=None,
        app_name="Education RAG",
        app_env="test",
        database_url="postgresql+psycopg://user:secret-password@localhost:5432/education_rag",
    )
    monkeypatch.setattr("app.main.load_settings", lambda: settings)
    monkeypatch.setattr("app.main.create_database_engine", lambda _: MagicMock())
    monkeypatch.setattr(
        "app.main.check_database_connection",
        lambda _: (_ for _ in ()).throw(DatabaseConnectionError("secret-password")),
    )

    assert run() == 1
    captured = capsys.readouterr()
    assert "PostgreSQL is unavailable" in captured.err
    assert "secret-password" not in captured.err


def test_run_summarizes_documents_without_printing_page_content(monkeypatch, capsys) -> None:
    settings = Settings(
        _env_file=None,
        app_name="Education RAG",
        app_env="test",
        database_url="postgresql+psycopg://user:password@localhost:5432/education_rag",
    )
    result = PDFLoadResult(
        info=DocumentInfo("id", "hash", "course/material.pdf", "material.pdf", 1),
        pages=[Document("conteudo confidencial da pagina")],
        total_pages=1,
    )
    monkeypatch.setattr("app.main.load_settings", lambda: settings)
    monkeypatch.setattr("app.main.create_database_engine", lambda _: MagicMock())
    monkeypatch.setattr("app.main.check_database_connection", lambda _: None)
    monkeypatch.setattr("app.main.enable_pgvector", lambda _: None)
    monkeypatch.setattr("app.main.load_documents", lambda _: [result])

    assert run() == 0
    output = capsys.readouterr().out
    assert "course/material.pdf" in output
    assert "hash" not in output
    assert "conteudo confidencial da pagina" not in output

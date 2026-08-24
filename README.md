# Education RAG

A aplicação descobre PDFs recursivamente em `data/documents` (ou em `DOCUMENTS_PATH`),
carrega cada página e mostra um resumo. Páginas sem texto podem ser digitalizadas e exigirão
OCR, que ainda não é suportado. Chunking, embeddings e perguntas ainda não foram implementados.

## Pre-requisitos

- Python 3.11 ou superior
- Docker Desktop com Docker Compose

## Executar localmente

No PowerShell, a partir da raiz do projeto:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e ".[dev]"
    Copy-Item .env.example .env
    docker compose up -d
    python -m app.main

A aplicacao carrega a configuracao, verifica PostgreSQL, habilita a extensao vector e
carrega os PDFs encontrados e encerra. O arquivo .env nao deve ser versionado.

## Qualidade

    pytest
    ruff check .
    ruff format --check .

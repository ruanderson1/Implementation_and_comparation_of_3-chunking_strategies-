"""PDF discovery and page-level extraction for the ingestion stage."""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentInfo:
    """Stable, public metadata that identifies a source PDF."""

    document_id: str
    document_hash: str
    source: str
    filename: str
    file_size_bytes: int


@dataclass
class PDFLoadResult:
    """Result of loading a single PDF without persisting ingestion state."""

    info: DocumentInfo
    pages: list[Document] = field(default_factory=list)
    total_pages: int = 0
    empty_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def text_pages(self) -> int:
        return len(self.pages) - len(self.empty_pages)


def _relative_source(path: Path, documents_path: Path) -> str:
    return path.relative_to(documents_path).as_posix()


def discover_pdf_files(documents_path: Path) -> list[Path]:
    """Find PDF files recursively, without traversing links outside the root."""
    documents_path.mkdir(parents=True, exist_ok=True)
    root = documents_path.resolve()
    files: list[Path] = []
    for directory, directories, filenames in os.walk(documents_path, followlinks=False):
        directory_path = Path(directory)
        directories[:] = [name for name in directories if not (directory_path / name).is_symlink()]
        for filename in filenames:
            path = directory_path / filename
            if path.suffix.lower() != ".pdf" or not path.is_file():
                continue
            try:
                path.resolve().relative_to(root)
            except ValueError:
                continue
            files.append(path)
    return sorted(files, key=lambda path: _relative_source(path, documents_path).casefold())


def calculate_sha256(path: Path) -> str:
    """Calculate a file hash incrementally, keeping memory use bounded."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def get_document_info(path: Path, documents_path: Path) -> DocumentInfo:
    """Build document metadata from the relative source path and file contents."""
    source = _relative_source(path, documents_path)
    return DocumentInfo(
        document_id=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        document_hash=calculate_sha256(path),
        source=source,
        filename=path.name,
        file_size_bytes=path.stat().st_size,
    )


def _normalise_page(
    page: Document, info: DocumentInfo, fallback_index: int, total_pages: int | None
) -> Document:
    original_metadata = dict(page.metadata)
    page_index = original_metadata.get("page", fallback_index)
    if not isinstance(page_index, int):
        page_index = fallback_index
    metadata = {
        "document_id": info.document_id,
        "document_hash": info.document_hash,
        "source": info.source,
        "filename": info.filename,
        "page": page_index + 1,
        "page_index": page_index,
        "page_label": original_metadata.get("page_label"),
        "total_pages": total_pages,
        "file_size_bytes": info.file_size_bytes,
    }
    return Document(page_content=page.page_content, metadata=metadata)


def load_pdf(path: Path, documents_path: Path) -> PDFLoadResult:
    """Load one PDF with ``PyPDFLoader``, keeping one LangChain document per page."""
    source = _relative_source(path, documents_path)
    fallback_info = DocumentInfo(
        document_id=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        document_hash="",
        source=source,
        filename=path.name,
        file_size_bytes=0,
    )
    try:
        info = get_document_info(path, documents_path)
    except OSError as exc:
        result = PDFLoadResult(info=fallback_info, failures=[f"{type(exc).__name__}: {exc}"])
        logger.exception("Failed to inspect PDF %s", source)
        return result
    result = PDFLoadResult(info=info)
    try:
        loader = PyPDFLoader(str(path))
        raw_pages: Iterable[Document] = loader.lazy_load()
        for fallback_index, raw_page in enumerate(raw_pages):
            raw_total = raw_page.metadata.get("total_pages")
            total_pages = raw_total if isinstance(raw_total, int) else None
            page = _normalise_page(raw_page, info, fallback_index, total_pages)
            result.pages.append(page)
            if not page.page_content.strip():
                page_number = page.metadata["page"]
                result.empty_pages.append(page_number)
                result.warnings.append(
                    f"{info.source}: página {page_number} sem texto; pode exigir OCR."
                )
        result.total_pages = len(result.pages)
        if result.pages and all(page.metadata["total_pages"] is None for page in result.pages):
            for page in result.pages:
                page.metadata["total_pages"] = result.total_pages
        elif result.pages:
            result.total_pages = int(result.pages[0].metadata["total_pages"])
    except Exception as exc:  # loader exceptions vary by PDF and backend
        result.failures.append(f"{type(exc).__name__}: {exc}")
        logger.exception("Failed to load PDF %s", info.source)
    return result


def load_documents(documents_path: Path) -> list[PDFLoadResult]:
    """Discover and load all PDFs under the configured documents directory."""
    return [load_pdf(path, documents_path) for path in discover_pdf_files(documents_path)]

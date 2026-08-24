from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from app.rag.ingestion import discover_pdf_files, get_document_info, load_pdf


def test_discover_pdf_files_is_recursive_case_insensitive_and_sorted(tmp_path: Path) -> None:
    (tmp_path / "z.PDF").write_bytes(b"z")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "a.pdf").write_bytes(b"a")
    (nested / "notes.txt").write_text("not a PDF")

    files = discover_pdf_files(tmp_path)

    assert [file.relative_to(tmp_path).as_posix() for file in files] == ["nested/a.pdf", "z.PDF"]


def test_document_info_has_stable_id_and_content_hash(tmp_path: Path) -> None:
    source = tmp_path / "same-name.pdf"
    source.write_bytes(b"first version")
    first = get_document_info(source, tmp_path)
    source.write_bytes(b"second version")
    second = get_document_info(source, tmp_path)
    other_directory = tmp_path / "other"
    other_directory.mkdir()
    other = other_directory / "same-name.pdf"
    other.write_bytes(b"second version")

    assert first.document_id == second.document_id
    assert first.document_hash != second.document_hash
    assert second.document_id != get_document_info(other, tmp_path).document_id


def test_load_pdf_normalises_metadata_and_reports_empty_pages(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "sub" / "article.pdf"
    source.parent.mkdir()
    source.write_bytes(b"PDF bytes")

    class FakeLoader:
        def __init__(self, _: str) -> None:
            pass

        def lazy_load(self):
            yield Document("page text", {"page": 0, "page_label": "i", "total_pages": 2})
            yield Document("   ", {"page": 1, "page_label": "2", "total_pages": 2})

    monkeypatch.setattr("app.rag.ingestion.PyPDFLoader", FakeLoader)
    result = load_pdf(source, tmp_path)

    assert result.total_pages == 2
    assert result.empty_pages == [2]
    assert result.pages[0].metadata["source"] == "sub/article.pdf"
    assert result.pages[0].metadata["page"] == 1
    assert result.pages[0].metadata["page_index"] == 0
    assert result.pages[0].metadata["page_label"] == "i"
    assert result.pages[1].metadata["document_id"] == result.info.document_id


def test_load_pdf_reports_loader_failure(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a PDF")

    class BrokenLoader:
        def __init__(self, _: str) -> None:
            pass

        def lazy_load(self):
            raise ValueError("invalid PDF")
            yield  # pragma: no cover

    monkeypatch.setattr("app.rag.ingestion.PyPDFLoader", BrokenLoader)
    result = load_pdf(source, tmp_path)

    assert not result.pages
    assert result.failures == ["ValueError: invalid PDF"]

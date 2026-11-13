"""Split extracted documents into metadata-preserving text chunks."""

import hashlib
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from langchain_text_splitters import RecursiveCharacterTextSplitter


_PAGE_HEADING = re.compile(r"(?m)^## Page[ \t]+(?P<number>\d+)[ \t]*\r?$")


def count_words(text: str) -> int:
    """Count whitespace-separated words in text."""
    return len(text.split())


_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    length_function=count_words,
    separators=["\n\n", "\n", ". ", " ", ""],
    is_separator_regex=False,
)


def _normalized_filename(filename: str) -> str:
    """Normalize a filename to a case-insensitive, Unicode-normalized basename."""
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    normalized = unicodedata.normalize("NFKC", basename).casefold()

    if not normalized:
        raise ValueError("Document filename must not be empty.")

    return normalized


def _page_spans(content: str) -> list[tuple[str, int, int]]:
    """Return page-number ranges identified by the extractor's Markdown headings."""
    headings = list(_PAGE_HEADING.finditer(content))
    return [
        (
            heading.group("number"),
            heading.start(),
            headings[index + 1].start() if index + 1 < len(headings) else len(content),
        )
        for index, heading in enumerate(headings)
    ]


def _pages_for_range(
    start: int,
    end: int,
    page_spans: list[tuple[str, int, int]],
) -> tuple[str, ...]:
    """Find page headings whose content ranges overlap a chunk range."""
    return tuple(
        page_number
        for page_number, page_start, page_end in page_spans
        if start < page_end and end > page_start
    )


def _source_pages(
    content: str,
    chunk: str,
    page_spans: list[tuple[str, int, int]],
) -> list[str]:
    """Return page numbers only when the chunk's source position is unambiguous."""
    if not page_spans:
        return []

    occurrences = []
    search_from = 0
    while True:
        position = content.find(chunk, search_from)
        if position < 0:
            break
        occurrences.append(
            _pages_for_range(position, position + len(chunk), page_spans)
        )
        search_from = position + 1

    if not occurrences or any(
        pages != occurrences[0] for pages in occurrences[1:]
    ):
        return []

    return list(occurrences[0])


def chunk_document(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Split a successful ``process_document`` result into deterministic chunks.

    Every chunk contains document-level metadata, its own text, a sequential
    index, a deterministic UUID, and PDF page numbers when their source ranges
    can be mapped to the extractor's page headings without ambiguity.
    """
    if not isinstance(document, Mapping):
        raise TypeError("document must be a mapping returned by process_document().")

    status = document.get("status")
    if status != "success":
        raise ValueError(
            f"Only documents with status='success' can be chunked; got {status!r}."
        )

    content = document.get("content")
    if not isinstance(content, str):
        raise TypeError("Document content must be a string.")
    if not content.strip():
        raise ValueError("Document content must not be empty.")

    filename = document.get("filename")
    if not isinstance(filename, str):
        raise TypeError("Document filename must be a string.")
    normalized_filename = _normalized_filename(filename)

    title = document.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Document title must be a non-empty string.")

    source_type = document.get("source_type")
    if not isinstance(source_type, str) or not source_type.strip():
        raise ValueError("Document source_type must be a non-empty string.")

    url = document.get("url")
    if url is not None and not isinstance(url, str):
        raise TypeError("Document url must be a string or None.")

    methods = document.get("extraction_method")
    if not isinstance(methods, list) or any(
        not isinstance(method, str) for method in methods
    ):
        raise TypeError("Document extraction_method must be a list of strings.")

    file_type = Path(filename.replace("\\", "/")).suffix.lower()
    if not file_type:
        raise ValueError("Document filename must include a file extension.")

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    document_key = f"{normalized_filename}\0{content_hash}"
    document_id = hashlib.sha256(document_key.encode("utf-8")).hexdigest()

    document_metadata = {
        "chunker_version":"v1",
        "document_id": document_id,
        "document_title": title,
        "source_url": url or "",
        "source_type": source_type,
        "source_group": "uploaded_document",
        "file_type": file_type,
        "extraction_method": ", ".join(sorted(set(methods))),
        "content_hash": content_hash,
    }

    split_texts = _SPLITTER.split_text(content)
    if not split_texts:
        raise ValueError("The document did not produce any text chunks.")

    page_spans = (
        _page_spans(content)
        if source_type.strip().lower() == "pdf"
        else []
    )

    chunks = []
    for chunk_index, chunk_text in enumerate(split_texts):
        chunk_metadata = dict(document_metadata)
        chunk_metadata.update(
            {
                "chunk_index": chunk_index,
                "chunk_id": str(
                    uuid5(
                        NAMESPACE_URL,
                        f"wonka:{document_id}:chunk:{chunk_index}",
                    )
                ),
                "source_pages": _source_pages(
                    content,
                    chunk_text,
                    page_spans,
                ),
                "content": chunk_text,
            }
        )
        chunks.append(chunk_metadata)

    return chunks

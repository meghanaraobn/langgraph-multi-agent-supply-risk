"""PDF -> per-page text extraction for the RAG ingestion pipeline.

Uses pdfplumber rather than a plain-text-only parser (e.g. pypdf) specifically
for its layout-aware table extraction: audit reports and disclosures in this
project's synthetic documents put structured data (certification schedules,
emissions figures) in tables that a naive text dump would jumble together
with surrounding prose.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass(frozen=True)
class PageContent:
    page_number: int
    """1-indexed, matching how a human would cite a page in this document."""

    text: str


def _render_table(table: list[list[str | None]]) -> str:
    rows = [" | ".join(cell or "" for cell in row) for row in table]
    return "\n".join(rows)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _table_already_in_text(table: list[list[str | None]], normalized_text: str) -> bool:
    """True if every row's cell content is already present in the page's
    plain-text extraction -- true whenever the table's text layer reads
    cleanly on its own (the common case for a simply laid out table),
    meaning the pipe-delimited rendering below would just duplicate it.
    False (i.e. worth appending) whenever extract_text() would jumble a
    table's reading order, which is the whole reason that rendering exists.
    """
    for row in table:
        cells = [cell for cell in row if cell]
        if not cells:
            continue
        if _normalize(" ".join(cells)) not in normalized_text:
            return False
    return True


def extract_pages(pdf_path: str | Path) -> list[PageContent]:
    """Extracts prose text plus any tables from every page of a PDF.

    A table is rendered as pipe-delimited rows and appended after the prose
    only if its content doesn't already appear in the plain-text extraction
    -- see _table_already_in_text. A page with neither text nor a table not
    already covered by that text is skipped entirely -- an empty page
    contributes nothing to ground a finding in and would only waste a chunk.
    """
    pages: list[PageContent] = []
    with pdfplumber.open(pdf_path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            normalized_text = _normalize(text)

            tables = [
                _render_table(t)
                for t in page.extract_tables()
                if t and not _table_already_in_text(t, normalized_text)
            ]

            combined = "\n\n".join([text, *tables]).strip()
            if combined:
                pages.append(PageContent(page_number=index, text=combined))

    return pages

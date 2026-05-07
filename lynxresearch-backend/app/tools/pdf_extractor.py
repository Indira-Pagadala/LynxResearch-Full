# app/tools/pdf_extractor.py

import io
import logging
import tempfile
import os
from typing import Optional
import fitz  # PyMuPDF
from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)


def extract_text_from_pdf_bytes(pdf_bytes: bytes, url: str = "") -> Optional[dict]:
    """
    Extract text and tables from PDF bytes using PyMuPDF.
    Returns structured document dict.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = []

        for page_num in range(min(len(doc), 40)):  # Max 40 pages
            page = doc[page_num]
            text = page.get_text("text")
            if text.strip():
                full_text.append(text)

        doc.close()

        combined_text = "\n\n".join(full_text)
        cleaned = clean_text(combined_text)

        if len(cleaned) < 100:
            return None

        return {
            "url": url,
            "title": os.path.basename(url) or "PDF Document",
            "raw_text": cleaned,
            "publication_date": None,
            "source_type": "pdf",
            "relevance_score": None,
        }

    except Exception as e:
        logger.error(f"PDF extraction failed for {url}: {e}")
        return None


def extract_tables_from_text(text: str) -> list[dict]:
    """
    Parse markdown-style and whitespace-aligned tables from extracted text.
    Returns list of {headers: list, rows: list[list], raw: str}
    """
    import re

    tables = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Detect markdown table: starts with |
        if line.startswith("|") and "|" in line[1:]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 2:
                parsed = _parse_markdown_table(table_lines)
                if parsed:
                    tables.append(parsed)
            continue

        i += 1

    return tables


def _parse_markdown_table(lines: list[str]) -> Optional[dict]:
    """Parse a markdown table into headers + rows."""
    try:
        rows = []
        for line in lines:
            # Skip separator lines like |---|---|
            if re.match(r"^\|[-:\s|]+\|$", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells:
                rows.append(cells)

        if len(rows) < 2:
            return None

        return {
            "headers": rows[0],
            "rows": rows[1:],
            "raw": "\n".join(lines),
        }
    except Exception:
        return None


async def process_pdf_documents(docs: list[dict]) -> list[dict]:
    """
    For docs with source_type='pdf' and raw_bytes,
    extract text and return updated docs list.
    """
    processed = []
    for doc in docs:
        if doc.get("source_type") == "pdf" and doc.get("raw_bytes"):
            extracted = extract_text_from_pdf_bytes(doc["raw_bytes"], doc.get("url", ""))
            if extracted:
                processed.append(extracted)
        else:
            processed.append(doc)
    return processed
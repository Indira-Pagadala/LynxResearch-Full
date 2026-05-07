# app/utils/text_cleaner.py

import re
import unicodedata
from typing import Optional


def clean_text(text: str) -> str:
    """
    Full pipeline: unicode normalize → strip boilerplate →
    collapse whitespace → remove non-printable chars.
    """
    if not text:
        return ""

    # Normalize unicode (handles weird apostrophes, dashes etc.)
    text = unicodedata.normalize("NFKC", text)

    # Remove HTML entities that slipped through
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)

    # Remove email addresses
    text = re.sub(r"\S+@\S+\.\S+", "", text)

    # Remove non-printable / control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Collapse multiple newlines → max 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # Strip lines that are just punctuation or numbers (nav bars, page numbers etc.)
    lines = text.split("\n")
    cleaned_lines = [
        line for line in lines
        if len(line.strip()) > 15 or line.strip() == ""
    ]
    text = "\n".join(cleaned_lines)

    return text.strip()


def truncate_to_tokens(text: str, max_tokens: int = 6000) -> str:
    """
    Rough token truncation (1 token ≈ 4 chars).
    Used before sending to Gemini to avoid context limit errors.
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...truncated for context limit...]"


def extract_numbers_from_text(text: str) -> list[dict]:
    """
    Find number + unit patterns. Returns clean short labels.
    """
    pattern = re.compile(
        r"([A-Z][^.!?\n]{5,60}?)"          # Lead-in phrase (short)
        r"[\s:]+?"
        r"(\$?\d[\d,]*\.?\d*)\s*"
        r"(billion|million|trillion|thousand|"
        r"%|percent|USD|INR|EUR|GBP|"
        r"Mt|GW|MW|kWh|crore|lakh|tonnes?)?\b",
        re.IGNORECASE,
    )
    results = []
    for match in pattern.finditer(text):
        label = match.group(1).strip()
        # Clean label: strip trailing conjunctions / partial phrases
        label = re.sub(r"\s+(and|or|the|a|an|is|was|were|of|in|for)$",
                       "", label, flags=re.IGNORECASE).strip()
        # Hard cap at 40 chars for chart readability
        if len(label) > 40:
            label = label[:37] + "..."
        try:
            value_str = match.group(2).replace("$", "").replace(",", "")
            value = float(value_str)
            if value <= 0:
                continue
            results.append({
                "value":      value,
                "unit":       match.group(3) or "",
                "context":    match.group(0)[:120],
                "stat_label": label,
            })
        except ValueError:
            continue
    return results


def split_into_chunks(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks for RAG embedding.
    Tries to split on sentence boundaries.
    """
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence.split())
        if current_len + sentence_len > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Overlap: keep last N words
            overlap_words = " ".join(current_chunk).split()[-overlap:]
            current_chunk = overlap_words + sentence.split()
            current_len = len(current_chunk)
        else:
            current_chunk.extend(sentence.split())
            current_len += sentence_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return [c for c in chunks if len(c.strip()) > 50]
# app/utils/deduplicator.py

import hashlib
from difflib import SequenceMatcher
from typing import Optional


def text_fingerprint(text: str) -> str:
    """SHA256 fingerprint of first 500 chars (fast near-duplicate detection)."""
    normalized = " ".join(text[:500].lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def deduplicate_documents(docs: list[dict]) -> list[dict]:
    """
    Remove near-duplicate documents from the scraped list.
    Uses URL dedup first, then fingerprint dedup.
    """
    seen_urls: set[str] = set()
    seen_fingerprints: set[str] = set()
    unique_docs = []

    for doc in docs:
        url = doc.get("url", "")
        text = doc.get("raw_text", "") or ""

        # Skip empty documents
        if len(text.strip()) < 100:
            continue

        # URL dedup
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Content fingerprint dedup
        fp = text_fingerprint(text)
        if fp in seen_fingerprints:
            continue
        seen_fingerprints.add(fp)

        unique_docs.append(doc)

    return unique_docs


def similarity_score(text1: str, text2: str) -> float:
    """
    Quick similarity check between two short texts.
    Returns 0.0 (different) to 1.0 (identical).
    """
    return SequenceMatcher(None, text1[:300], text2[:300]).ratio()


def deduplicate_statistics(stats: list[dict]) -> list[dict]:
    """
    Remove duplicate statistics entries.
    Two stats are duplicate if same label + same value.
    """
    seen: set[str] = set()
    unique = []
    for stat in stats:
        key = f"{stat.get('stat_label', '').lower()}_{stat.get('value', '')}"
        if key not in seen:
            seen.add(key)
            unique.append(stat)
    return unique
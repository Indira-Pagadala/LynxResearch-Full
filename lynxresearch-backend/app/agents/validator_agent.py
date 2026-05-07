# app/agents/validator_agent.py

import re
import logging
import uuid
from sqlalchemy import select
from app.agents.state import ResearchState
from app.utils.progress_emitter import emit_progress
from app.database import AsyncSessionLocal
from app.models.citation import Citation
from app.models.document import ScrapedDocument
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def validator_agent(state: ResearchState) -> dict:
    run_id  = state["run_id"]
    content = state.get("validated_content", "")
    docs    = state.get("scraped_documents", [])

    await emit_progress(run_id, "validating", 10, "Extracting and resolving citations...")

    if not content:
        return {"errors": ["Validator: no content to validate"]}

    # ── Extract all citation keys ─────────────────────────────
    citation_pattern = re.compile(r"\[ref:([A-Za-z0-9_\-]+)\]")
    citation_keys    = list(set(citation_pattern.findall(content)))
    bracket_mentions = _extract_bracket_mentions(content)
    logger.info(f"[Validator] {len(citation_keys)} unique citation keys found")

    # ── Build lookup maps from scraped docs ───────────────────
    domain_url_map = _build_domain_map(docs)
    url_title_map  = {d.get("url", ""): d.get("title", "") for d in docs}

    # ── Resolve each key ──────────────────────────────────────
    resolved: dict[str, dict] = {}
    unresolved_keys: list[str] = []

    for key in citation_keys:
        result = _resolve_citation(key, domain_url_map, url_title_map, docs)
        if result:
            resolved[key] = result
        else:
            unresolved_keys.append(key)

    # Also resolve inline mentions like [Genpact] -> numbered citations.
    mention_to_key: dict[str, str] = {}
    for mention in bracket_mentions:
        match = _resolve_mention_to_doc(mention, docs)
        if not match:
            continue
        pseudo_key = f"src_{match['doc_index']}"
        mention_to_key[mention] = pseudo_key
        if pseudo_key not in resolved:
            resolved[pseudo_key] = _make_citation(
                key=pseudo_key,
                url=match["url"],
                title=match["title"],
                year=None,
            )

    logger.info(
        f"[Validator] Resolved: {len(resolved)}, "
        f"Unresolved (hallucinated): {len(unresolved_keys)}"
    )

    # ── Replace [ref:KEY] with numbered superscripts ──────────
    key_to_number: dict[str, int] = {}
    counter = 1

    def replace_citation(match):
        nonlocal counter
        key = match.group(1)
        if key not in resolved:
            return ""
        if key not in key_to_number:
            key_to_number[key] = counter
            counter += 1
        return f"<sup>[{key_to_number[key]}]</sup>"

    validated_content = citation_pattern.sub(replace_citation, content)
    validated_content = _replace_bracket_mentions_with_citations(
        validated_content, mention_to_key, key_to_number
    )

    if not key_to_number and docs:
        for i, doc in enumerate(docs[:15], start=1):
            pseudo_key = f"src_{i}"
            key_to_number[pseudo_key] = i
            resolved[pseudo_key] = _make_citation(
                key=pseudo_key,
                url=doc.get("url", ""),
                title=(doc.get("title") or doc.get("url") or f"Source {i}"),
                year=None,
            )

    # ── Build references section ──────────────────────────────
    references_md = _build_references_section(key_to_number, resolved)

    # Replace or append references section
    if re.search(r"#+\s*References", validated_content, re.IGNORECASE):
        validated_content = re.sub(
            r"#+\s*References.*$",
            references_md,
            validated_content,
            flags=re.DOTALL | re.MULTILINE,
        )
    else:
        validated_content += f"\n\n{references_md}"

    validated_content = _sanitize_report_markdown(validated_content)
    validated_content = _truncate_after_references(validated_content)

    # ── Quality checks ────────────────────────────────────────
    issues = _run_quality_checks(validated_content)

    await emit_progress(
        run_id, "validating", 70,
        f"Resolved {len(resolved)}/{len(citation_keys)} citations. Saving..."
    )

    await _save_citations(run_id, resolved, docs)

    await emit_progress(
        run_id, "validating", 100,
        f"Validation complete. {len(issues)} issues."
    )

    return {
        "final_markdown":     validated_content,
        "citations":          list(resolved.values()),
        "validation_issues":  issues,
        "current_stage":      "building_pdf",
        "progress":           80,
    }


# ── Helpers ───────────────────────────────────────────────────

def _build_domain_map(docs: list[dict]) -> dict[str, str]:
    from urllib.parse import urlparse
    mapping: dict[str, str] = {}
    for doc in docs:
        url = doc.get("url", "")
        if not url:
            continue
        try:
            netloc = urlparse(url).netloc.replace("www.", "").lower()
            base   = netloc.split(".")[0]
            if base and base not in mapping:
                mapping[base] = url
        except Exception:
            pass
    return mapping


def _resolve_citation(
    key: str,
    domain_map: dict[str, str],
    url_title_map: dict[str, str],
    docs: list[dict],
) -> dict | None:
    """
    Try to match citation key to a real scraped document.
    Key formats: Domain_Year  or  DomainSuffix_Year
    """
    parts       = key.split("_")
    domain_hint = parts[0].lower()
    year_hint   = parts[-1] if len(parts) > 1 and parts[-1].isdigit() else None

    # 1. Exact domain base match
    url = domain_map.get(domain_hint)
    if url:
        title = url_title_map.get(url, url)
        return _make_citation(key, url, title, year_hint)

    # 2. Substring match against all URLs
    for doc in docs:
        doc_url = doc.get("url", "").lower()
        if domain_hint in doc_url:
            url   = doc.get("url", "")
            title = doc.get("title", url)
            return _make_citation(key, url, title, year_hint)

    # 3. Substring match against titles
    for doc in docs:
        title = (doc.get("title") or "").lower()
        if domain_hint in title:
            url   = doc.get("url", "")
            title = doc.get("title", url)
            return _make_citation(key, url, title, year_hint)

    return None


def _make_citation(key: str, url: str, title: str, year: str | None) -> dict:
    year_str = year or "n.d."
    clean    = (title or url)[:120]
    apa      = f"{clean}. ({year_str}). Retrieved from {url}"
    return {
        "citation_key": key,
        "url":          url,
        "title":        title,
        "year":         year_str,
        "apa_string":   apa,
    }


def _build_references_section(
    key_to_number: dict[str, int],
    resolved: dict[str, dict],
) -> str:
    lines = ["## References\n"]
    sorted_keys = sorted(key_to_number.items(), key=lambda x: x[1])

    for key, num in sorted_keys:
        if key in resolved:
            url = resolved[key].get("url", "")
            lines.append(
                f"{num}. {resolved[key]['apa_string']} "
                f"[Link]({url})"
            )
    return "\n".join(lines)


def _run_quality_checks(content: str) -> list[str]:
    issues = []
    wc = len(content.split())
    if wc < 3000:
        issues.append(f"Report too short: {wc} words")
    if "Executive Summary" not in content:
        issues.append("Missing Executive Summary")
    if "References" not in content:
        issues.append("Missing References section")
    leftover = re.findall(r"\[ref:[^\]]+\]", content)
    if leftover:
        issues.append(f"Unresolved citations: {leftover[:3]}")
    return issues


async def _save_citations(run_id: str, resolved: dict, docs: list[dict]):
    async with AsyncSessionLocal() as db:
        try:
            run_uuid = uuid.UUID(run_id)
            rows = await db.execute(
                select(ScrapedDocument.id, ScrapedDocument.url).where(ScrapedDocument.run_id == run_uuid)
            )
            url_to_doc_id = {url: doc_id for doc_id, url in rows.all() if url}

            for key, data in resolved.items():
                url = data.get("url", "")
                document_id = url_to_doc_id.get(url)
                if not document_id:
                    continue
                db.add(Citation(
                    run_id=run_uuid,
                    document_id=document_id,
                    citation_key=key,
                    apa_string=data.get("apa_string"),
                ))
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"[Validator] Citation DB save failed: {e}")


def _extract_bracket_mentions(content: str) -> list[str]:
    """
    Capture legacy inline source mentions like [Genpact], excluding
    citations like [ref:...], numeric markers [3], and markdown links.
    """
    mention_pattern = re.compile(r"\[([A-Za-z][A-Za-z0-9& ._\-]{1,50})\]")
    mentions: list[str] = []
    seen: set[str] = set()
    for m in mention_pattern.findall(content):
        low = m.lower()
        if low.startswith("ref:"):
            continue
        if m.isdigit():
            continue
        if m.lower() in {"link", "source"}:
            continue
        if m not in seen:
            seen.add(m)
            mentions.append(m)
    return mentions


def _resolve_mention_to_doc(mention: str, docs: list[dict]) -> dict | None:
    target = mention.lower().strip()
    for idx, doc in enumerate(docs):
        url = doc.get("url", "")
        title = (doc.get("title") or url or "").strip()
        if not url:
            continue
        if target in title.lower() or target in url.lower():
            return {"doc_index": idx, "url": url, "title": title}
    return None


def _replace_bracket_mentions_with_citations(
    content: str,
    mention_to_key: dict[str, str],
    key_to_number: dict[str, int],
) -> str:
    for mention, key in mention_to_key.items():
        if key not in key_to_number:
            continue
        num = key_to_number[key]
        content = re.sub(
            rf"(?<!\()(\[{re.escape(mention)}\])",
            f"[{num}](#ref-{num})",
            content,
        )
    # Convert citation superscripts generated from [ref:*]
    content = re.sub(r"<sup>\[(\d+)\]</sup>", r"[\1](#ref-\1)", content)
    return content


def _sanitize_report_markdown(content: str) -> str:
    """
    Lightweight cleanup only: remove malformed/noise lines and empty sections.
    """
    # Remove common placeholder/noise artifacts.
    cleaned = re.sub(r"\[Image\s*\d+:[^\]]*\]", "", content, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*share sensitive information.*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"^\s*here's how you know.*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"^\s*official websites use.*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Remove empty headings.
    lines = cleaned.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*#{2,3}\s+.+$", line):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or re.match(r"^\s*#{2,3}\s+.+$", lines[j]):
                i += 1
                continue
        out.append(line)
        i += 1
    return "\n".join(out).strip()


def _truncate_after_references(content: str) -> str:
    """
    Hard stop: References must always be the final section.
    """
    lines = content.splitlines()
    ref_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"^\s*#{1,3}\s*References\s*$", line, flags=re.IGNORECASE):
            ref_idx = i
            break
    if ref_idx == -1:
        return content

    end_idx = len(lines)
    for i in range(ref_idx + 1, len(lines)):
        if re.match(r"^\s*#{1,3}\s+", lines[i]):
            end_idx = i
            break
    return "\n".join(lines[:end_idx]).strip()
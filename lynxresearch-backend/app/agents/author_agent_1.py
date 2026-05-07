# app/agents/author_agent_1.py

import re
import logging

from app.agents.state import ResearchState
from app.utils.text_cleaner import truncate_to_tokens
from app.utils.progress_emitter import emit_progress
from app.utils.llm_factory import get_author_llm
from app.config import get_settings
from langchain_core.messages import SystemMessage, HumanMessage
from app.utils.llm_limiter import (
    groq_call_with_retry,
    trim_prompt_to_budget,
    estimate_message_tokens,
)

logger   = logging.getLogger(__name__)
settings = get_settings()

STYLE_CONFIGS = {
    "business": {
        "tone":     "formal business/consulting",
        "focus":    "market size, revenue, investment, competitive landscape, ROI, industry players",
        "sections": [
            "Executive Summary",
            "1. Introduction & Industry Background",
            "2. Methodology",
            "3. Market Overview & Size",
            "4. Key Growth Drivers & Market Barriers",
        ],
        "citation_style": "industry report style [ref:Org_Year]",
        "avoid":    "avoid clinical/medical terminology unless the topic demands it",
    },
    "medical": {
        "tone":     "clinical and evidence-based",
        "focus":    "pathophysiology, symptoms, diagnosis, treatment options, patient outcomes, clinical trials, epidemiology, prevalence",
        "sections": [
            "Executive Summary",
            "1. Introduction & Clinical Background",
            "2. Methodology & Data Sources",
            "3. Epidemiology & Prevalence",
            "4. Pathophysiology & Diagnosis",
        ],
        "citation_style": "medical research style [ref:Author_Year]",
        "avoid":    "avoid business/market language — focus on patients, clinicians, outcomes",
    },
    "academic": {
        "tone":     "formal academic",
        "focus":    "literature review, theoretical frameworks, research gaps, empirical evidence, scholarly debate",
        "sections": [
            "Abstract",
            "1. Introduction",
            "2. Literature Review",
            "3. Methodology",
            "4. Findings & Analysis",
        ],
        "citation_style": "APA academic [ref:Author_Year]",
        "avoid":    "avoid marketing language — prioritise scholarly rigour",
    },
    "technical": {
        "tone":     "technical and precise",
        "focus":    "architecture, implementation, specifications, algorithms, performance benchmarks, engineering tradeoffs",
        "sections": [
            "Executive Summary",
            "1. Introduction & Technical Context",
            "2. Methodology",
            "3. Technical Architecture & Implementation",
            "4. Performance Analysis & Benchmarks",
        ],
        "citation_style": "technical documentation [ref:Source_Year]",
        "avoid":    "avoid vague generalisations — use precise technical language",
    },
    "general": {
        "tone":     "clear and accessible for a general audience",
        "focus":    "balanced overview: what it is, why it matters, key facts, current state, future outlook",
        "sections": [
            "Executive Summary",
            "1. Introduction & Background",
            "2. Methodology",
            "3. Overview & Key Facts",
            "4. Key Drivers & Challenges",
        ],
        "citation_style": "accessible [ref:Source_Year]",
        "avoid":    "avoid jargon — explain technical terms when used",
    },
    "policy": {
        "tone":     "policy and governance focused",
        "focus":    "regulatory environment, government initiatives, compliance, public impact, stakeholder analysis, policy recommendations",
        "sections": [
            "Executive Summary",
            "1. Introduction & Policy Context",
            "2. Methodology",
            "3. Regulatory Landscape",
            "4. Key Policy Drivers & Barriers",
        ],
        "citation_style": "policy brief [ref:Org_Year]",
        "avoid":    "avoid purely commercial framing — focus on public interest and governance",
    },
}


async def author_agent_1(state: ResearchState) -> dict:
    """
    Author Agent 1 — writes the first half of the report.
    Uses Groq (llama-3.3-70b-versatile) — no Gemini quota used.
    LLM imported lazily inside get_author_llm() — no metaclass conflict.
    """
    run_id       = state["run_id"]
    topic        = state["topic"]
    report_style = state.get("report_style", "general")
    docs         = state.get("scraped_documents", [])
    key_stats    = state.get("key_statistics", [])
    chart_paths  = state.get("chart_paths", [])
    tables       = state.get("extracted_tables", [])

    style_cfg = STYLE_CONFIGS.get(report_style, STYLE_CONFIGS["general"])

    await emit_progress(
        run_id, "authoring", 5,
        f"Author 1 writing [{report_style}] report via Groq..."
    )

    # get_author_llm() imports ChatGroq lazily — no metaclass conflict
    llm     = get_author_llm(temperature=0.4)
    context = _build_context(topic, docs, key_stats, tables)

    chart_block = _build_chart_block(
        chart_paths, start_index=1, max_charts=2
    )

    await emit_progress(run_id, "authoring", 20, "Writing sections 1–4...")

    system_prompt = f"""You are a senior researcher writing a high-quality professional research report.

    REPORT STYLE: {report_style.upper()}
    TONE: {style_cfg['tone']}
    FOCUS: {style_cfg['focus']}
    IMPORTANT: {style_cfg['avoid']}

    ABSOLUTE RULES:
    1. Every factual claim MUST have a citation: {style_cfg['citation_style']}
    2. Write in flowing paragraphs — NO bullet points in body text
    3. Use ## for section headers, ### for sub-headers
    4. EMBED CHARTS using EXACTLY this markdown syntax:
    ![Figure N: Caption](EXACT_PATH_FROM_LIST)
    5. Bold key terms with **term**
    6. Keep output dense, lengthy, verbose and evidence-led, avoid filler
    7. Include at least ONE markdown table with real data in section 3 or 4
    8. Prioritise relevance to topic over verbosity"""

    sections_prompt = f"""Write the first half of a detailed [{report_style}] research report on:
"{topic}"

SECTIONS TO WRITE (strict minimum word counts):
{_format_sections(style_cfg['sections'])}

WORD REQUIREMENTS:
- This half should target 5000-6500 words total
- Cover each section with strong evidence and smooth transitions
- Section 3 must include a markdown table of key data

CHARTS TO EMBED (copy paths EXACTLY):
{chart_block}

MANDATORY TABLE: In section 3, include a properly formatted markdown table like:
| Year | Metric | Value | Source |
|------|--------|-------|--------|
| 2020 | ... | ... | ... |

RESEARCH DATA AND SOURCES:
{context}

End with a transition paragraph leading into the forecast/developments section.
Keep claims tightly connected to cited sources."""

    sections_prompt = trim_prompt_to_budget(sections_prompt, max_tokens=2200)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=sections_prompt),
    ]
    logger.info(f"[Author1] Prompt estimate tokens={estimate_message_tokens(messages)}")

    response = await groq_call_with_retry(
        llm,
        messages,
        max_retries=4,
        label=f"Author1 run={run_id[:8]}",
    )

    author1_content = response.content

    # Force inject charts if LLM forgot to embed them
    author1_content = _force_inject_charts(
        author1_content, chart_paths[:2], start_index=1
    )

    paragraphs = [p.strip() for p in author1_content.split("\n\n") if p.strip()]
    last_paras = (
        "\n\n".join(paragraphs[-2:])
        if len(paragraphs) >= 2
        else author1_content[-800:]
    )

    await emit_progress(
        run_id, "authoring", 50,
        "Author 1 done. Passing to Author 2..."
    )

    return {
        "report_outline":          [],
        "author1_content":         author1_content,
        "author1_last_paragraph":  last_paras,
        "current_stage":           "authoring_2",
        "progress":                60,
    }


# ── Helpers ───────────────────────────────────────────────────

def _build_chart_block(
    chart_paths: list[str],
    start_index: int,
    max_charts: int,
) -> str:
    if not chart_paths:
        return "No charts available for this run."
    lines = ["Embed these charts in your sections (copy paths EXACTLY):"]
    for i, path in enumerate(chart_paths[:max_charts]):
        fig_num = start_index + i
        label   = _chart_label(path, fig_num)
        lines.append(
            f"\nFigure {fig_num}:\n"
            f"![Figure {fig_num}: {label}]({path})"
        )
    return "\n".join(lines)


def _force_inject_charts(
    content: str,
    chart_paths: list[str],
    start_index: int,
) -> str:
    """
    If the LLM forgot to embed a chart, inject it after
    the third ## heading automatically.
    """
    for i, path in enumerate(chart_paths):
        if path in content:
            continue
        fig_num   = start_index + i
        label     = _chart_label(path, fig_num)
        embed_str = f"\n\n![Figure {fig_num}: {label}]({path})\n\n"

        headings = list(re.finditer(r"\n##[^#]", content))
        if len(headings) >= 3:
            inject_at  = headings[2].end()
            next_blank = content.find("\n\n", inject_at)
            if next_blank == -1:
                next_blank = len(content)
            content = (
                content[:next_blank]
                + embed_str
                + content[next_blank:]
            )
        else:
            content += embed_str

    return content


def _chart_label(path: str, index: int) -> str:
    from pathlib import Path
    stem = Path(path).stem
    if "forecast" in stem: return "Market/Trend Forecast Projection"
    if "stats"    in stem: return "Key Statistics Overview"
    if "table"    in stem: return f"Data Summary Table {index}"
    if "gemini"   in stem: return f"Analytical Chart {index}"
    return f"Research Figure {index}"


def _format_sections(sections: list[str]) -> str:
    return "\n".join(f"## {s}" for s in sections)


def _build_context(
    topic:   str,
    docs:    list[dict],
    stats:   list[dict],
    tables:  list[dict],
) -> str:
    parts = [f"TOPIC: {topic}\n"]

    parts.append("KEY SOURCE EXCERPTS:")
    for doc in docs[:12]:
        text = doc.get("raw_text", "")
        if not text:
            continue
        url    = doc.get("url", "")
        domain = _domain(url)
        parts.append(
            f"\n[{domain}]:\n"
            f"{text[:700].replace(chr(10), ' ')}..."
        )

    if stats:
        parts.append("\nKEY DATA POINTS:")
        for s in stats[:15]:
            parts.append(
                f"- {s.get('value')} {s.get('unit', '')} — "
                f"{s.get('stat_label', '')[:80]} "
                f"[{_domain(s.get('source_url', ''))}]"
            )

    if tables:
        parts.append("\nDATA TABLES:")
        for i, t in enumerate(tables[:3]):
            parts.append(
                f"\nTable {i+1}: "
                f"{' | '.join(t.get('headers', []))}"
            )
            for row in t.get("rows", [])[:5]:
                parts.append("  " + " | ".join(str(c) for c in row))

    return truncate_to_tokens("\n".join(parts), max_tokens=1800)


def _domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        d = urlparse(url).netloc.replace("www.", "")
        return d.split(".")[0].capitalize()
    except Exception:
        return "Source"
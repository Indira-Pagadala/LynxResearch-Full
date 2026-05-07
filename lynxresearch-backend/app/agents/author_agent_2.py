# app/agents/author_agent_2.py

import re
import logging

from app.agents.state import ResearchState
from app.utils.text_cleaner import truncate_to_tokens
from app.utils.progress_emitter import emit_progress
from app.utils.llm_factory import get_author_llm
from app.config import get_settings
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.author_agent_1 import (
    STYLE_CONFIGS,
    _force_inject_charts,
    _chart_label,
    _domain,
)
from app.utils.llm_limiter import (
    groq_call_with_retry,
    trim_prompt_to_budget,
    estimate_message_tokens,
)

logger   = logging.getLogger(__name__)
settings = get_settings()

SECOND_HALF_SECTIONS = {
    "medical": [
        "5. Treatment Options & Clinical Guidelines",
        "6. Recent Research & Clinical Trials",
        "7. Patient Outcomes & Quality of Life",
        "8. Challenges & Gaps in Care",
        "9. Conclusion & Clinical Recommendations",
    ],
    "business": [
        "5. Market Forecast & Scenarios",
        "6. Regional Analysis",
        "7. Competitive Landscape",
        "8. Risks & Investment Considerations",
        "9. Conclusion & Strategic Recommendations",
    ],
    "academic": [
        "5. Results & Discussion",
        "6. Theoretical Implications",
        "7. Limitations",
        "8. Future Research Directions",
        "9. Conclusion",
    ],
    "technical": [
        "5. System Architecture & Design",
        "6. Implementation & Performance",
        "7. Comparative Analysis",
        "8. Limitations & Future Work",
        "9. Conclusion",
    ],
    "general": [
        "5. Current State & Recent Developments",
        "6. Regional / Global Perspective",
        "7. Future Outlook",
        "8. Challenges & Considerations",
        "9. Conclusion & Key Takeaways",
    ],
    "policy": [
        "5. Policy Recommendations",
        "6. Stakeholder Analysis",
        "7. Implementation Roadmap",
        "8. Risks & Governance Challenges",
        "9. Conclusion & Policy Outlook",
    ],
}


async def author_agent_2(state: ResearchState) -> dict:
    """
    Author Agent 2 — writes second half of report.
    Uses Groq (llama-3.3-70b-versatile) — no Gemini quota used.
    Receives author1_last_paragraph for seamless continuation.
    LLM imported lazily inside get_author_llm() — no metaclass conflict.
    """
    run_id            = state["run_id"]
    topic             = state["topic"]
    report_style      = state.get("report_style", "general")
    author1_content   = state.get("author1_content", "")
    author1_last_para = state.get("author1_last_paragraph", "")
    forecast_results  = state.get("forecast_results", [])
    key_stats         = state.get("key_statistics", [])
    chart_paths       = state.get("chart_paths", [])
    docs              = state.get("scraped_documents", [])

    style_cfg = STYLE_CONFIGS.get(report_style, STYLE_CONFIGS["general"])
    sections  = SECOND_HALF_SECTIONS.get(
        report_style, SECOND_HALF_SECTIONS["general"]
    )

    await emit_progress(
        run_id, "authoring", 55,
        f"Author 2 writing [{report_style}] second half via Groq..."
    )

    # get_author_llm() imports ChatGroq lazily — no metaclass conflict
    llm = get_author_llm(temperature=0.4)

    forecast_ctx = _build_forecast_context(forecast_results)
    stats_ctx    = _build_stats_context(key_stats)
    sources_ctx  = _build_sources_context(docs)

    # Charts for Author 2 — use remaining charts
    remaining_charts = (
        chart_paths[2:]
        if len(chart_paths) > 2
        else chart_paths[1:]
    )
    if not remaining_charts and chart_paths:
        remaining_charts = chart_paths

    chart_block        = _build_chart_block(remaining_charts, start_index=3)
    sections_formatted = "\n".join(f"## {s}" for s in sections)

    system_prompt = f"""You are completing the second half of a detailed {report_style}-style research report.

STYLE: {report_style.upper()} — {style_cfg['tone']}
FOCUS: {style_cfg['focus']}
IMPORTANT: {style_cfg['avoid']}

RULES:
1. Continue seamlessly — same tone, same citation style {style_cfg['citation_style']}
2. Every factual claim MUST have a citation
3. Write in flowing paragraphs — NO bullet points in body text
4. EMBED CHARTS using EXACT markdown: ![Figure N: Caption](EXACT_PATH)
5. References section: properly formatted numbered list with full URLs
6. Keep output dense, lengthy, verbose and evidence-led, avoid filler
7. Include at least ONE markdown table with real data in any section
8. Maintain strict relevance to topic and cited evidence"""

    prompt = f"""Continue the {report_style}-style research report on:
"{topic}"

PREVIOUS AUTHOR ENDED WITH:
---
{author1_last_para}
---
Your first sentence MUST flow naturally from the above ending.

YOUR SECTIONS (strict minimum word counts):
{sections_formatted}
## References

WORD REQUIREMENTS:
- This half should target 5000-6500 words total
- Keep each section substantive with evidence and data
- Conclusion should be practical and specific
- References: complete numbered list with URLs

MANDATORY TABLE: Include a markdown data table in one of your sections:
| Category | Detail | Data | Source |
|----------|--------|------|--------|

{chart_block}

FORECAST DATA (cite specific numbers):
{forecast_ctx}

KEY STATISTICS:
{stats_ctx}

SOURCES FOR CITATIONS (use these URLs in your references):
{sources_ctx}

REFERENCES FORMAT — write every reference like this:
1. Title of Article. (Year). Retrieved from https://full-url-here.com

Embed at least 2 charts. Maintain high factual grounding."""
    prompt = trim_prompt_to_budget(prompt, max_tokens=2200)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt),
    ]
    logger.info(f"[Author2] Prompt estimate tokens={estimate_message_tokens(messages)}")

    response = await groq_call_with_retry(
        llm,
        messages,
        max_retries=4,
        label=f"Author2 run={run_id[:8]}",
    )

    author2_content = response.content

    # Force inject charts if LLM forgot to embed them
    author2_content = _force_inject_charts(
        author2_content,
        remaining_charts[:3],
        start_index=3,
    )

    full_content = _merge_report(
        topic, report_style, author1_content, author2_content
    )

    await emit_progress(
        run_id, "authoring", 100,
        "Both authors complete. Merging report..."
    )

    return {
        "author2_content":   author2_content,
        "validated_content": full_content,
        "current_stage":     "validating",
        "progress":          70,
    }


# ── Report merger ─────────────────────────────────────────────

def _merge_report(
    topic:        str,
    report_style: str,
    author1:      str,
    author2:      str,
) -> str:
    style_label = report_style.capitalize()
    toc = f"""# {topic}
## A Comprehensive {style_label} Research Report

---

*Generated by LynxResearch — Autonomous Multi-Agent Research System*

---

## Table of Contents

1. Executive Summary
2. Introduction & Background
3. Methodology
4. Overview & Analysis (Part I)
5. Key Drivers & Analysis (Part II)
6. Forecast / Developments
7. Regional / Global Perspective
8. Competitive / Comparative Analysis
9. Risks & Limitations
10. Conclusion & Recommendations
11. References

---

"""
    return toc + author1.strip() + "\n\n---\n\n" + author2.strip()


# ── Context builders ──────────────────────────────────────────

def _build_chart_block(
    chart_paths: list[str],
    start_index: int,
) -> str:
    if not chart_paths:
        return "No additional charts available."
    lines = ["CHARTS TO EMBED (copy paths EXACTLY):\n"]
    for i, path in enumerate(chart_paths[:4]):
        fig_num = start_index + i
        label   = _chart_label(path, fig_num)
        lines.append(
            f"Figure {fig_num} ({label}):\n"
            f"![Figure {fig_num}: {label}]({path})\n"
        )
    return "\n".join(lines)


def _build_forecast_context(results: list[dict]) -> str:
    if not results:
        return "No quantitative forecast available."
    lines = []
    for f in results:
        label  = f.get("label", "Series")
        unit   = f.get("unit", "")
        model  = f.get("model_used", "").upper()
        yrs    = f.get("future_years", [])
        base   = f.get("base_values", [])
        bull   = f.get("bull_values", [])
        bear   = f.get("bear_values", [])
        mape   = f.get("mape")
        header = f"\n{label} ({unit}) — {model}"
        if mape:
            header += f" | MAPE {mape:.1f}%"
        lines.append(header)
        for y, b, bu, be in zip(yrs, base, bull, bear):
            lines.append(
                f"  {y}: Base={b:,.2f}  "
                f"Bull={bu:,.2f}  Bear={be:,.2f}"
            )
    return truncate_to_tokens("\n".join(lines), max_tokens=500)


def _build_stats_context(stats: list[dict]) -> str:
    if not stats:
        return "No statistics extracted."
    text = "\n".join(
        f"- {s.get('value')} {s.get('unit', '')} — "
        f"{s.get('stat_label', '')[:100]}"
        for s in stats[:15]
    )
    return truncate_to_tokens(text, max_tokens=300)


def _build_sources_context(docs: list[dict]) -> str:
    if not docs:
        return "No sources available."
    text = "\n".join(
        f"- [{_domain(d.get('url', ''))}] "
        f"{d.get('title', '')} — {d.get('url', '')}"
        for d in docs[:25]
    )
    return truncate_to_tokens(text, max_tokens=700)
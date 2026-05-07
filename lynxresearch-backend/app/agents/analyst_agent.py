# app/agents/analyst_agent.py

import logging
import asyncio
import re

from app.agents.state import ResearchState
from app.tools.forecaster import extract_time_series, forecast_time_series
from app.tools.chart_generator import (
    generate_forecast_chart,
    generate_chart_with_gemini,
    generate_statistics_bar_chart,
    generate_table_chart,
)
from app.tools.pdf_extractor import extract_tables_from_text
from app.utils.text_cleaner import extract_numbers_from_text
from app.utils.deduplicator import deduplicate_statistics
from app.utils.progress_emitter import emit_progress
from app.utils.llm_factory import get_flash_llm
from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


async def analyst_agent(state: ResearchState) -> dict:
    """
    Analyst Agent Node.

    1. Extracts tables + statistics from every scraped document
    2. Finds time-series data and runs Prophet/ARIMA forecasting
    3. Generates matplotlib charts (pure Python, no LLM quota)
    4. Uses Gemini Flash for AI-powered chart specs (rate-limited)
    5. Falls back to brute-force chart if nothing else worked

    Gemini Flash used only for chart spec calls — minimal quota impact.
    No Groq used here — all chart work is pure Python or Gemini Flash.
    """
    run_id = state["run_id"]
    topic  = state["topic"]
    docs   = state.get("scraped_documents", [])

    await emit_progress(
        run_id, "analyst", 5,
        "Extracting tables and statistics from documents..."
    )

    # get_flash_llm() imports lazily — no metaclass conflict
    llm_flash = get_flash_llm(temperature=0.1)

    # ─────────────────────────────────────────────────────────
    # STEP 1 — Extract tables, stats, text from all docs
    # ─────────────────────────────────────────────────────────
    all_tables:          list[dict] = []
    all_stats:           list[dict] = []
    combined_for_series: list[str]  = []

    for doc in docs:
        text = doc.get("raw_text", "")
        if not text:
            continue

        tables = extract_tables_from_text(text)
        for t in tables:
            if len(t.get("rows", [])) >= 2:
                all_tables.append({
                    **t,
                    "source_url": doc.get("url", ""),
                })

        nums = extract_numbers_from_text(text)
        for n in nums:
            n["source_url"] = doc.get("url", "")
        all_stats.extend(nums)
        combined_for_series.append(text[:4000])

    all_stats        = deduplicate_statistics(all_stats)
    meaningful_stats = [
        s for s in all_stats
        if s.get("unit") and float(s.get("value", 0)) > 0
    ][:20]

    logger.info(
        f"[Analyst] {len(all_tables)} tables, "
        f"{len(meaningful_stats)} stats, "
        f"{len(docs)} docs"
    )

    await emit_progress(
        run_id, "analyst", 20,
        f"Found {len(all_tables)} tables, "
        f"{len(meaningful_stats)} stats. Running forecasts..."
    )

    # ─────────────────────────────────────────────────────────
    # STEP 2 — Time-series + forecasting
    # ─────────────────────────────────────────────────────────
    combined_text = "\n\n".join(combined_for_series[:20])
    raw_series    = extract_time_series(combined_text)
    logger.info(f"[Analyst] {len(raw_series)} time-series candidates")

    forecast_results: list[dict] = []
    chart_paths:      list[str]  = []

    for series in raw_series[:settings.MAX_TIMESERIES_TO_MODEL]:
        result = forecast_time_series(series)
        if result:
            forecast_results.append(result)
            path = generate_forecast_chart(result, run_id)
            if path:
                chart_paths.append(path)
                logger.info(f"[Analyst] Forecast chart: {path}")

    await emit_progress(
        run_id, "analyst", 40,
        f"{len(forecast_results)} forecasts done. "
        "Generating static visualisations..."
    )

    # ─────────────────────────────────────────────────────────
    # STEP 3 — Statistics bar chart (pure matplotlib)
    # ─────────────────────────────────────────────────────────
    if meaningful_stats:
        path = generate_statistics_bar_chart(
            meaningful_stats[:10],
            f"Key Statistics — {topic}",
            run_id,
        )
        if path:
            chart_paths.append(path)
            logger.info(f"[Analyst] Stats chart: {path}")

    # ─────────────────────────────────────────────────────────
    # STEP 4 — Table figure images (pure matplotlib)
    # ─────────────────────────────────────────────────────────
    for i, table in enumerate(all_tables[:4]):
        path = generate_table_chart(
            table,
            f"Data Table {i + 1} — {topic}",
            run_id,
        )
        if path:
            chart_paths.append(path)
            logger.info(f"[Analyst] Table chart {i+1}: {path}")

    # ─────────────────────────────────────────────────────────
    # STEP 5 — Gemini Flash AI charts (sequential, rate-limited)
    # ─────────────────────────────────────────────────────────
    await emit_progress(
        run_id, "analyst", 60,
        "Generating AI-powered chart visualisations..."
    )

    gemini_requests: list[tuple[str, str, str]] = []

    for i, table in enumerate(all_tables[:2]):
        if len(table.get("rows", [])) < 2:
            continue
        gemini_requests.append((
            f"Research data table {i+1} about {topic}",
            _table_to_string(table),
            "auto",
        ))

    if meaningful_stats:
        stats_str = "\n".join(
            f"{s.get('stat_label', 'stat')}: "
            f"{s['value']} {s.get('unit', '')}"
            for s in meaningful_stats[:10]
        )
        gemini_requests.append((
            f"Key statistics for {topic}",
            stats_str,
            "horizontal_bar",
        ))

    # Run sequentially with delay — polite to Gemini Flash quota
    for desc, data_str, chart_type in gemini_requests:
        try:
            path = await _rate_limited_gemini_chart(
                desc, data_str, chart_type, run_id, llm_flash
            )
            if path:
                chart_paths.append(path)
                logger.info(f"[Analyst] Gemini chart: {path}")
            await asyncio.sleep(settings.GEMINI_FLASH_DELAY_SECONDS)
        except Exception as e:
            logger.warning(f"[Analyst] Gemini chart failed: {e}")

    # ─────────────────────────────────────────────────────────
    # STEP 6 — Fallback: force at least 1 chart from raw text
    # ─────────────────────────────────────────────────────────
    if not chart_paths:
        logger.warning(
            "[Analyst] No charts generated — running text fallback..."
        )
        fallback = _fallback_chart_from_text(topic, combined_text, run_id)
        if fallback:
            chart_paths.extend(fallback)

    logger.info(
        f"[Analyst] Complete — "
        f"{len(chart_paths)} charts, "
        f"{len(forecast_results)} forecasts, "
        f"{len(all_tables)} tables, "
        f"{len(meaningful_stats)} stats"
    )

    await emit_progress(
        run_id, "analyst", 100,
        f"Analysis complete: {len(chart_paths)} charts, "
        f"{len(forecast_results)} forecast models"
    )

    return {
        "extracted_tables":  all_tables[:10],
        "time_series_data":  raw_series,
        "forecast_results":  forecast_results,
        "chart_paths":       chart_paths,
        "key_statistics":    meaningful_stats,
        "current_stage":     "authoring",
        "progress":          50,
    }


# ── Private helpers ───────────────────────────────────────────

async def _rate_limited_gemini_chart(
    data_description: str,
    data_payload: str,
    chart_type: str,
    run_id: str,
    llm_flash,
) -> str | None:
    """
    Wraps generate_chart_with_gemini so the internal LLM call
    goes through the Gemini rate limiter.
    Temporarily replaces ainvoke then restores it.
    """
    from app.utils.gemini_limiter import gemini_flash_call

    original_ainvoke = llm_flash.ainvoke

    async def _limited_ainvoke(prompt, **kwargs):
        return await gemini_flash_call(llm_flash, prompt)

    llm_flash.ainvoke = _limited_ainvoke

    try:
        result = await generate_chart_with_gemini(
            data_description=data_description,
            data_payload=data_payload,
            chart_type=chart_type,
            run_id=run_id,
            llm_flash=llm_flash,
        )
        return result
    finally:
        # Always restore — even if exception raised
        llm_flash.ainvoke = original_ainvoke


def _table_to_string(table: dict) -> str:
    """Convert table dict to pipe-separated string for LLM."""
    headers = table.get("headers", [])
    rows    = table.get("rows", [])
    lines   = [" | ".join(str(h) for h in headers)]
    for row in rows[:12]:
        lines.append(" | ".join(str(c) for c in row))
    return "\n".join(lines)


def _fallback_chart_from_text(
    topic: str,
    text: str,
    run_id: str,
) -> list[str]:
    """
    Last resort: scan raw text for Year + Value patterns
    and build a simple historical trend line chart.
    No LLM needed — pure regex + matplotlib.
    
    Stricter validation to avoid random/irrelevant charts:
    - Requires at least 4 data points
    - Years must be in reasonable range (2000-2035)
    - Values must be consistent (not random page numbers etc.)
    - Must find a clear unit to confirm it's actual data
    """
    paths   = []
    pattern = re.compile(
        r"(20[0-3]\d)[^\\d]{1,20}(\d+\.?\d*)\s*"
        r"(billion|million|trillion|%|USD|INR|GW|MW|crore|TWh|GWh|tons|tonnes)",
        re.IGNORECASE,
    )
    matches = pattern.findall(text)

    if len(matches) >= 4:  # Require at least 4 data points
        seen_years: set[int]   = set()
        years:      list[int]  = []
        values:     list[float] = []
        unit = ""

        for m in matches[:15]:
            yr = int(m[0])
            # Only accept reasonable year range
            if yr < 2000 or yr > 2035:
                continue
            if yr in seen_years:
                continue
            seen_years.add(yr)
            try:
                val = float(m[1])
                # Filter out obviously wrong values (likely page numbers etc.)
                if val <= 0 or val > 1e12:
                    continue
                years.append(yr)
                values.append(val)
                if m[2] and not unit:
                    unit = m[2]
            except ValueError:
                continue

        # Need at least 4 valid data points with a unit
        if len(years) >= 4 and unit:
            data = {
                "label":             f"{topic} — Extracted Trend ({unit})",
                "historical_years":  years,
                "historical_values": values,
                "future_years":      [],
                "base_values":       [],
                "bull_values":       [],
                "bear_values":       [],
                "unit":              unit,
                "model_used":        "historical only",
                "mape":              None,
            }
            path = generate_forecast_chart(data, run_id)
            if path:
                paths.append(path)
                logger.info(f"[Analyst] Fallback chart saved: {path}")

    return paths
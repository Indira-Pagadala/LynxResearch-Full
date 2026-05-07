# app/tools/chart_generator.py

import os
import uuid
import json
import logging
import asyncio
import re
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Brand palette ─────────────────────────────────────────────
COLORS = [
    "#1A237E", "#43A047", "#FF8F00", "#E53935",
    "#7B1FA2", "#00838F", "#AD1457", "#4E342E",
]


def _ensure_charts_dir(run_id: str) -> Path:
    chart_dir = Path(settings.CHARTS_DIR) / run_id
    chart_dir.mkdir(parents=True, exist_ok=True)
    return chart_dir


# ─────────────────────────────────────────────────────────────
# 1.  FORECAST CHART  (always works — pure matplotlib)
# ─────────────────────────────────────────────────────────────
def generate_forecast_chart(forecast_data: dict, run_id: str) -> Optional[str]:
    """
    Historical + bull/base/bear forecast line chart.
    Returns absolute path to PNG.
    """
    try:
        chart_dir = _ensure_charts_dir(run_id)
        chart_path = chart_dir / f"forecast_{uuid.uuid4().hex[:8]}.png"

        label       = forecast_data.get("label", "Market Forecast")
        unit        = forecast_data.get("unit", "")
        hist_years  = forecast_data.get("historical_years", [])
        hist_values = forecast_data.get("historical_values", [])
        future_yrs  = forecast_data.get("future_years", [])
        base        = forecast_data.get("base_values", [])
        bull        = forecast_data.get("bull_values", [])
        bear        = forecast_data.get("bear_values", [])
        mape        = forecast_data.get("mape")
        model_used  = forecast_data.get("model_used", "").upper()

        fig, ax = plt.subplots(figsize=(11, 6))
        fig.patch.set_facecolor("#FAFAFA")
        ax.set_facecolor("#FAFAFA")

        if hist_years and hist_values:
            ax.plot(hist_years, hist_values, "o-",
                    color="#1A237E", lw=2.5, ms=7,
                    label="Historical", zorder=5)

        if future_yrs and base:
            if bull and bear:
                ax.fill_between(future_yrs, bear, bull,
                                alpha=0.18, color="#43A047",
                                label="Bull–Bear Range")
            ax.plot(future_yrs, base,  "s--", color="#43A047", lw=2.5, ms=7,
                    label="Base Forecast")
            ax.plot(future_yrs, bull,  "^:",  color="#FF8F00", lw=1.8, ms=5,
                    label="Bull Scenario")
            ax.plot(future_yrs, bear,  "v:",  color="#E53935", lw=1.8, ms=5,
                    label="Bear Scenario")

            if hist_years and hist_values:
                ax.plot([hist_years[-1], future_yrs[0]],
                        [hist_values[-1], base[0]],
                        "--", color="#43A047", lw=1.5, alpha=0.5)

        mape_str = f"  |  MAPE: {mape:.1f}%" if mape else ""
        ax.set_title(f"{label}\nModel: {model_used}{mape_str}",
                     fontsize=13, fontweight="bold", pad=14)
        ax.set_xlabel("Year", fontsize=11)
        y_label = f"Value ({unit})" if unit else "Value"
        ax.set_ylabel(y_label, fontsize=11)
        ax.legend(loc="upper left", fontsize=9, framealpha=0.7)
        ax.grid(True, ls="--", alpha=0.4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"[Chart] Forecast chart saved: {chart_path}")
        return str(chart_path)
    except Exception as e:
        logger.error(f"[Chart] Forecast chart failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# 2.  GEMINI → JSON → MATPLOTLIB  (reliable pipeline)
# ─────────────────────────────────────────────────────────────
async def generate_chart_with_gemini(
    data_description: str,
    data_payload: str,
    chart_type: str,
    run_id: str,
    llm_flash,
) -> Optional[str]:
    """
    Step 1: Ask Gemini Flash to extract/structure the data as JSON.
    Step 2: We render the chart ourselves in matplotlib.
    This is far more reliable than asking Gemini to write executable code.
    """
    # ── Step 1: Gemini extracts structured chart JSON ─────────
    prompt = f"""You are a data extraction assistant. 
Analyse the following data and return ONLY a valid JSON object — no markdown, no explanation.

Data description: {data_description}
Raw data: {data_payload}

Return this exact JSON structure:
{{
  "chart_type": "bar" or "line" or "pie" or "horizontal_bar",
  "title": "descriptive chart title",
  "x_label": "x axis label",
  "y_label": "y axis label with unit",
  "series": [
    {{
      "name": "series name",
      "x": [list of x values or category labels],
      "y": [list of numeric y values]
    }}
  ]
}}

Rules:
- Choose chart_type based on data: time series → line, categories → bar, 
  parts of whole → pie, long labels → horizontal_bar
- All y values must be numbers (floats or ints)
- Maximum 12 data points per series
- Maximum 3 series total
- Return ONLY the JSON, nothing else"""

    try:
        response = await llm_flash.ainvoke(prompt)
        raw = response.content.strip()

        # Strip markdown fences if Gemini added them anyway
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        raw = raw.strip()

        chart_spec = json.loads(raw)
        logger.info(f"[Chart] Gemini returned chart spec: {chart_spec.get('title')}")

        # ── Step 2: Render with matplotlib ────────────────────
        return _render_chart_from_spec(chart_spec, run_id)

    except json.JSONDecodeError as e:
        logger.error(f"[Chart] Gemini returned invalid JSON: {e}\nRaw: {raw[:300]}")
        return None
    except Exception as e:
        logger.error(f"[Chart] Gemini chart pipeline failed: {e}")
        return None


def _render_chart_from_spec(spec: dict, run_id: str) -> Optional[str]:
    """
    Renders a chart from a structured spec dict produced by Gemini.
    Handles: bar, line, pie, horizontal_bar.
    """
    try:
        chart_dir  = _ensure_charts_dir(run_id)
        chart_path = chart_dir / f"gemini_{uuid.uuid4().hex[:8]}.png"

        chart_type = spec.get("chart_type", "bar")
        title      = spec.get("title", "Chart")
        x_label    = spec.get("x_label", "")
        y_label    = spec.get("y_label", "")
        series     = spec.get("series", [])

        if not series:
            logger.warning("[Chart] No series data in spec")
            return None

        fig, ax = plt.subplots(figsize=(11, 6))
        fig.patch.set_facecolor("#FAFAFA")
        ax.set_facecolor("#FAFAFA")

        if chart_type == "pie":
            _render_pie(ax, series[0], title)
        elif chart_type == "horizontal_bar":
            _render_horizontal_bar(ax, series, title, x_label, y_label)
        elif chart_type == "line":
            _render_line(ax, series, title, x_label, y_label)
        else:
            _render_bar(ax, series, title, x_label, y_label)

        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"[Chart] Gemini chart rendered: {chart_path}")
        return str(chart_path)

    except Exception as e:
        logger.error(f"[Chart] Render from spec failed: {e}")
        return None


def _render_bar(ax, series: list, title: str, x_label: str, y_label: str):
    n_series = len(series)
    x_vals   = series[0].get("x", [])
    n_bars   = len(x_vals)
    x_pos    = np.arange(n_bars)
    width    = 0.8 / max(n_series, 1)

    for i, s in enumerate(series):
        y = [float(v) for v in s.get("y", [])]
        offset = (i - n_series / 2 + 0.5) * width
        bars = ax.bar(x_pos + offset, y, width=width * 0.9,
                      color=COLORS[i % len(COLORS)],
                      label=s.get("name", ""), alpha=0.88)
        # Value labels on bars
        for bar, val in zip(bars, y):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() * 1.01,
                    f"{val:,.1f}", ha="center", va="bottom",
                    fontsize=8, color="#333333")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(
        [str(v) for v in x_vals],
        rotation=30 if n_bars > 6 else 0,
        ha="right" if n_bars > 6 else "center",
        fontsize=9,
    )
    _style_ax(ax, title, x_label, y_label, n_series > 1)


def _render_line(ax, series: list, title: str, x_label: str, y_label: str):
    for i, s in enumerate(series):
        x = s.get("x", [])
        y = [float(v) for v in s.get("y", [])]
        ax.plot(x, y, "o-", color=COLORS[i % len(COLORS)],
                lw=2.5, ms=7, label=s.get("name", ""))
        # Annotate last point
        if x and y:
            ax.annotate(f"{y[-1]:,.1f}",
                        xy=(x[-1], y[-1]),
                        xytext=(5, 5), textcoords="offset points",
                        fontsize=8, color=COLORS[i % len(COLORS)])

    ax.set_xticks(range(len(series[0].get("x", []))))
    ax.set_xticklabels(
        [str(v) for v in series[0].get("x", [])],
        rotation=30 if len(series[0].get("x", [])) > 6 else 0,
        ha="right", fontsize=9,
    )
    _style_ax(ax, title, x_label, y_label, len(series) > 1)


def _render_horizontal_bar(ax, series: list, title: str, x_label: str, y_label: str):
    s = series[0]
    labels = [str(v) for v in s.get("x", [])]
    values = [float(v) for v in s.get("y", [])]

    y_pos = np.arange(len(labels))
    bars  = ax.barh(y_pos, values,
                    color=COLORS[:len(labels)], alpha=0.88)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() * 1.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,.1f}", va="center", fontsize=9)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    _style_ax(ax, title, y_label, x_label, False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _render_pie(ax, series: dict, title: str):
    labels = [str(v) for v in series.get("x", [])]
    values = [float(v) for v in series.get("y", [])]
    explode = [0.03] * len(values)
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.1f%%",
        colors=COLORS[:len(values)], explode=explode,
        startangle=140, pctdistance=0.82,
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)


def _style_ax(ax, title: str, x_label: str, y_label: str, show_legend: bool):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=14)
    if x_label:
        ax.set_xlabel(x_label, fontsize=11)
    if y_label:
        ax.set_ylabel(y_label, fontsize=11)
    if show_legend:
        ax.legend(fontsize=9, framealpha=0.7)
    ax.grid(True, axis="y", ls="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ─────────────────────────────────────────────────────────────
# 3.  STATISTICS BAR CHART  (always works — pure matplotlib)
# ─────────────────────────────────────────────────────────────
def generate_statistics_bar_chart(
    stats: list[dict], title: str, run_id: str
) -> Optional[str]:
    """
    Clean, readable horizontal bar chart with proper short labels.
    """
    try:
        if not stats:
            return None

        # ── Deduplicate and clean stats ───────────────────────
        seen_vals: set = set()
        clean_stats = []
        for s in stats:
            label = s.get("stat_label", "").strip()
            val   = s.get("value", 0)
            unit  = s.get("unit", "")

            # Skip if label is a sentence fragment (starts lowercase or too long)
            if not label or len(label) < 4:
                continue
            # Skip duplicate values
            key = round(float(val), 1)
            if key in seen_vals:
                continue
            seen_vals.add(key)

            # Final label cleanup
            label = label.strip(".,;:")
            if len(label) > 38:
                label = label[:35] + "..."
            clean_stats.append({**s, "stat_label": label})

        clean_stats = clean_stats[:8]
        if len(clean_stats) < 2:
            return None

        chart_dir  = _ensure_charts_dir(run_id)
        chart_path = chart_dir / f"stats_{uuid.uuid4().hex[:8]}.png"

        labels = [s["stat_label"] for s in clean_stats]
        values = [float(s.get("value", 0)) for s in clean_stats]
        units  = [s.get("unit", "") for s in clean_stats]

        # Normalize all values to same scale if units differ wildly
        max_val = max(values) if values else 1

        fig_height = max(5, len(labels) * 0.75 + 1.5)
        fig, ax = plt.subplots(figsize=(12, fig_height))
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#F8F9FC")

        # Gradient-like color by value magnitude
        norm_vals  = [v / max_val for v in values]
        bar_colors = [
            plt.cm.Blues(0.4 + 0.5 * nv)  # type: ignore
            for nv in norm_vals
        ]

        y_pos = np.arange(len(labels))
        bars  = ax.barh(
            y_pos, values,
            color=bar_colors,
            height=0.6,
            edgecolor="white",
            linewidth=0.8,
        )

        # Value labels inside or outside bar
        for bar, val, unit in zip(bars, values, units):
            w = bar.get_width()
            unit_str = f" {unit}" if unit else ""
            label_str = (
                f"{val:,.0f}{unit_str}"
                if val >= 10
                else f"{val:,.2f}{unit_str}"
            )
            # Place label outside bar for visibility
            ax.text(
                w + max_val * 0.01,
                bar.get_y() + bar.get_height() / 2,
                label_str,
                va="center", ha="left",
                fontsize=9.5, color="#1A237E", fontweight="bold",
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=10, color="#333333")
        ax.invert_yaxis()

        ax.set_title(title, fontsize=14, fontweight="bold",
                     color="#0D1B4B", pad=16)
        ax.set_xlabel("Value", fontsize=11, color="#555555")

        # Remove clutter
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False)
        ax.set_xlim(0, max_val * 1.20)  # Space for labels
        ax.grid(axis="x", ls="--", alpha=0.35, color="#CCCCCC")

        # Subtle background band on alternate rows
        for i in range(len(labels)):
            if i % 2 == 0:
                ax.axhspan(i - 0.4, i + 0.4, color="#EEF2FF",
                           alpha=0.4, zorder=0)

        plt.tight_layout(pad=1.5)
        plt.savefig(chart_path, dpi=160, bbox_inches="tight",
                    facecolor="#FFFFFF")
        plt.close(fig)
        logger.info(f"[Chart] Stats chart saved: {chart_path}")
        return str(chart_path)

    except Exception as e:
        logger.error(f"[Chart] Stats chart failed: {e}")
        return None

# ─────────────────────────────────────────────────────────────
# 4.  TABLE → CHART  (for extracted markdown tables)
# ─────────────────────────────────────────────────────────────
def generate_table_chart(table: dict, title: str, run_id: str) -> Optional[str]:
    """
    Render a scraped data table as a matplotlib table figure.
    Always embeds in PDF even when no numeric chart is possible.
    """
    try:
        headers = table.get("headers", [])
        rows    = table.get("rows", [])
        if not headers or not rows:
            return None

        chart_dir  = _ensure_charts_dir(run_id)
        chart_path = chart_dir / f"table_{uuid.uuid4().hex[:8]}.png"

        # Limit size
        headers = headers[:6]
        rows    = rows[:12]
        rows    = [r[:6] for r in rows]

        n_rows = len(rows) + 1   # +1 for header
        n_cols = len(headers)

        fig_h = max(3, n_rows * 0.45 + 1)
        fig, ax = plt.subplots(figsize=(11, fig_h))
        fig.patch.set_facecolor("#FAFAFA")
        ax.axis("off")

        table_data = [headers] + rows
        tbl = ax.table(
            cellText=table_data,
            loc="center",
            cellLoc="left",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.auto_set_column_width(col=list(range(n_cols)))

        # Style header row
        for col in range(n_cols):
            cell = tbl[0, col]
            cell.set_facecolor("#0D1B4B")
            cell.set_text_props(color="white", fontweight="bold")
            cell.set_height(0.12)

        # Style body rows
        for row in range(1, n_rows):
            bg = "#F5F7FA" if row % 2 == 0 else "white"
            for col in range(n_cols):
                tbl[row, col].set_facecolor(bg)
                tbl[row, col].set_height(0.1)

        ax.set_title(title, fontsize=12, fontweight="bold",
                     pad=10, color="#0D1B4B")
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"[Chart] Table chart saved: {chart_path}")
        return str(chart_path)
    except Exception as e:
        logger.error(f"[Chart] Table chart failed: {e}")
        return None
# app/agents/state.py

from typing import TypedDict, Annotated
from operator import add


class ResearchState(TypedDict):
    # ── Identity ──────────────────────────────────────────────
    run_id: str
    topic: str
    report_style: str   # business | academic | medical | technical | general | policy

    # ── Scout outputs ─────────────────────────────────────────
    search_queries: list[str]
    urls_to_crawl: list[str]
    scraped_documents: Annotated[list[dict], add]

    # ── Analyst outputs ───────────────────────────────────────
    extracted_tables: list[dict]
    time_series_data: list[dict]
    forecast_results: list[dict]
    chart_paths: Annotated[list[str], add]
    key_statistics: list[dict]

    # ── Author shared memory ──────────────────────────────────
    report_outline: list[dict]
    author1_content: str
    author1_last_paragraph: str
    author2_content: str

    # ── Validator outputs ─────────────────────────────────────
    citations: list[dict]
    validated_content: str
    validation_issues: Annotated[list[str], add]

    # ── Final output ──────────────────────────────────────────
    final_markdown: str
    pdf_path: str

    # ── Pipeline control ──────────────────────────────────────
    current_stage: str
    progress: int
    errors: Annotated[list[str], add]
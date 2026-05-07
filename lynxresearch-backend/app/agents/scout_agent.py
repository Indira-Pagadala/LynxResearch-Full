# app/agents/scout_agent.py

import logging
import asyncio
import uuid

from app.agents.state import ResearchState
from app.tools.search_tool import collect_all_urls
from app.tools.web_scraper import scrape_urls_batch, score_relevance
from app.tools.pdf_extractor import process_pdf_documents
from app.utils.deduplicator import deduplicate_documents
from app.utils.text_cleaner import clean_text
from app.utils.progress_emitter import emit_progress
from app.utils.llm_factory import get_flash_llm
from app.database import AsyncSessionLocal
from app.models.document import ScrapedDocument
from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


async def scout_agent(state: ResearchState) -> dict:
    """
    Scout Agent Node.

    1. Generates search queries via Gemini Flash (1 call only)
    2. Fetches URLs + pre-extracted content via Tavily
    3. Scrapes remaining URLs not covered by Tavily
    4. Deduplicates, scores relevance, persists to DB

    No Groq quota used here — only Gemini Flash for query generation.
    """
    run_id = state["run_id"]
    topic  = state["topic"]

    await emit_progress(run_id, "scout", 5, "Generating research queries...")

    # ── Single Gemini Flash call for query generation ─────────
    # get_flash_llm() imports lazily — no metaclass conflict
    llm = get_flash_llm(temperature=0.3)

    # ── Step 1: Search ────────────────────────────────────────
    try:
        queries, urls, tavily_docs = await collect_all_urls(topic, llm)
        logger.info(
            f"[Scout] {len(urls)} URLs, "
            f"{len(tavily_docs)} Tavily pre-extracted docs"
        )
    except Exception as e:
        logger.error(f"[Scout] Search failed: {e}")
        return {"errors": [f"Scout search failed: {str(e)}"]}

    await emit_progress(
        run_id, "scout", 20,
        f"Found {len(urls)} sources. "
        f"{len(tavily_docs)} already extracted by Tavily..."
    )

    # ── Step 2: Clean Tavily docs ─────────────────────────────
    for doc in tavily_docs:
        doc["raw_text"]        = clean_text(doc.get("raw_text", ""))
        doc["relevance_score"] = score_relevance(doc, topic)

    # ── Step 3: Scrape URLs not covered by Tavily ─────────────
    tavily_urls    = {d["url"] for d in tavily_docs}
    urls_to_scrape = [u for u in urls if u not in tavily_urls]

    additional_docs: list[dict] = []
    if urls_to_scrape:
        await emit_progress(
            run_id, "scout", 35,
            f"Scraping {len(urls_to_scrape)} additional sources..."
        )
        raw_scraped     = await scrape_urls_batch(urls_to_scrape[:30])
        additional_docs = await process_pdf_documents(raw_scraped)
        for doc in additional_docs:
            doc["relevance_score"] = score_relevance(doc, topic)

    # ── Step 4: Merge + deduplicate ───────────────────────────
    all_docs = tavily_docs + additional_docs
    all_docs.sort(
        key=lambda x: x.get("relevance_score") or 0,
        reverse=True,
    )
    unique_docs = deduplicate_documents(all_docs)
    unique_docs = unique_docs[:50]

    logger.info(f"[Scout] {len(unique_docs)} unique documents after dedup")
    await emit_progress(
        run_id, "scout", 60,
        f"{len(unique_docs)} documents. Saving to database..."
    )

    # ── Step 5: Persist to DB ─────────────────────────────────
    async with AsyncSessionLocal() as db:
        try:
            for doc in unique_docs:
                db_doc = ScrapedDocument(
                    run_id=uuid.UUID(run_id),
                    url=doc.get("url", ""),
                    title=doc.get("title"),
                    raw_text=doc.get("raw_text"),
                    publication_date=None,
                    source_type=doc.get("source_type", "html"),
                    relevance_score=doc.get("relevance_score"),
                )
                db.add(db_doc)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"[Scout] DB save failed: {e}")

    await emit_progress(
        run_id, "scout", 100,
        f"Scout complete: {len(unique_docs)} documents collected"
    )

    return {
        "search_queries":    queries,
        "urls_to_crawl":     urls,
        "scraped_documents": unique_docs,
        "current_stage":     "analyst",
        "progress":          25,
    }
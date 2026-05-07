# app/tools/search_tool.py
# Gemini Flash used ONLY here for query generation — 1 call per run

import asyncio
import logging
from tavily import TavilyClient
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SKIP_DOMAINS = [
    "youtube.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "tiktok.com", "pinterest.com",
    "amazon.com", "ebay.com", "flipkart.com",
]


def _tavily_search_sync(query: str, max_results: int = 8) -> list[dict]:
    try:
        client   = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_raw_content=True,
            include_answer=False,
        )
        results = []
        for r in response.get("results", []):
            url = r.get("url", "")
            if not url or any(d in url for d in SKIP_DOMAINS):
                continue
            results.append({
                "title":       r.get("title", ""),
                "url":         url,
                "snippet":     r.get("content", ""),
                "raw_content": r.get("raw_content") or r.get("content", ""),
            })
        return results
    except Exception as e:
        logger.error(f"[Tavily] Search failed for '{query}': {e}")
        return []


async def fetch_search_results(query: str, max_results: int = 8) -> list[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _tavily_search_sync, query, max_results
    )


async def generate_search_queries(topic: str, llm) -> list[str]:
    """
    Uses Gemini Flash to generate 10 research queries.
    This is the ONLY Gemini call in the entire pipeline.
    """
    from app.utils.gemini_limiter import gemini_flash_call

    prompt = f"""You are a research analyst. Generate exactly 10 diverse, specific search queries
to thoroughly research the topic: "{topic}"

Rules:
- Cover: market size, statistics, forecasts, key players, challenges,
  recent developments, regulations, regional breakdown, trends
- Each query must be specific and return data-rich sources
- Output ONLY the queries, one per line, no numbering, no extra text

Topic: {topic}"""

    try:
        response = await gemini_flash_call(llm, prompt)
        queries = [
            q.strip()
            for q in response.content.strip().split("\n")
            if q.strip() and len(q.strip()) > 10
        ]
        if queries:
            return queries[:10]
    except Exception as e:
        logger.warning(f"[Search] Gemini query generation failed, using fallback queries: {e}")

    # Fallback for quota/rate-limit failures: keep run grounded with deterministic searches.
    return [
        f"{topic} market size statistics",
        f"{topic} trends 2024 2025",
        f"{topic} forecast CAGR report",
        f"{topic} key players analysis",
        f"{topic} government policy regulation",
        f"{topic} challenges opportunities",
        f"{topic} regional breakdown data",
        f"{topic} case study industry report",
        f"{topic} latest developments",
        f"{topic} official data sources",
    ]


async def collect_all_urls(
    topic: str, llm
) -> tuple[list[str], list[str], list[dict]]:
    queries = await generate_search_queries(topic, llm)
    logger.info(f"[Search] {len(queries)} queries for: {topic!r}")

    tasks       = [fetch_search_results(q, max_results=8) for q in queries]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls:     set[str]  = set()
    unique_urls:   list[str] = []
    enriched_docs: list[dict] = []

    for result_set in all_results:
        if isinstance(result_set, Exception):
            logger.warning(f"[Search] Task failed: {result_set}")
            continue
        for item in result_set:
            url = item.get("url", "").strip()
            if not url or not url.startswith("http"):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            unique_urls.append(url)

            raw = item.get("raw_content", "") or item.get("snippet", "")
            if raw and len(raw.strip()) > 100:
                enriched_docs.append({
                    "url":              url,
                    "title":            item.get("title", url),
                    "raw_text":         raw,
                    "publication_date": None,
                    "source_type":      "html",
                    "relevance_score":  None,
                })

    logger.info(
        f"[Search] {len(unique_urls)} URLs, "
        f"{len(enriched_docs)} pre-extracted docs"
    )
    return queries, unique_urls[:settings.MAX_URLS_TO_CRAWL], enriched_docs
# app/tools/web_scraper.py

import asyncio
import httpx
import trafilatura
import logging
from datetime import date
from typing import Optional
from app.config import get_settings
from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)
settings = get_settings()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


async def scrape_url(url: str, client: httpx.AsyncClient) -> Optional[dict]:
    """
    Scrape a single URL using trafilatura for clean text extraction.
    Returns structured document dict or None on failure.
    """
    try:
        response = await client.get(url, timeout=settings.CRAWL_TIMEOUT_SECONDS)
        if response.status_code != 200:
            return None

        content_type = response.headers.get("content-type", "")
        if "pdf" in content_type:
            # Hand off to PDF extractor
            return {"url": url, "source_type": "pdf", "raw_bytes": response.content}

        html = response.text

        # trafilatura extraction — best-in-class for article text
        extracted = trafilatura.extract(
            html,
            include_tables=True,
            include_links=False,
            include_images=False,
            no_fallback=False,
            favor_precision=False,   # Favor recall for research
        )

        if not extracted or len(extracted.strip()) < 150:
            return None

        # Extract metadata
        metadata = trafilatura.extract_metadata(html)
        title = metadata.title if metadata else None
        pub_date = None
        if metadata and metadata.date:
            try:
                from dateutil.parser import parse as date_parse
                pub_date = date_parse(metadata.date).date().isoformat()
            except Exception:
                pass

        return {
            "url": url,
            "title": title or url,
            "raw_text": clean_text(extracted),
            "publication_date": pub_date,
            "source_type": "html",
            "relevance_score": None,
        }

    except httpx.TimeoutException:
        logger.warning(f"Timeout scraping: {url}")
        return None
    except Exception as e:
        logger.warning(f"Error scraping {url}: {e}")
        return None


async def scrape_urls_batch(urls: list[str]) -> list[dict]:
    """
    Scrape multiple URLs in parallel batches.
    Returns all successfully scraped documents.
    """
    results = []
    batch_size = settings.CRAWL_BATCH_SIZE

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            tasks = [scrape_url(url, client) for url in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    continue
                if result and result.get("raw_text"):
                    results.append(result)
                elif result and result.get("source_type") == "pdf":
                    # Will be processed by pdf_extractor
                    results.append(result)

            logger.info(f"Scraped batch {i//batch_size + 1}: {len(results)} docs so far")
            await asyncio.sleep(0.5)  # Polite delay between batches

    return results


def score_relevance(doc: dict, topic: str) -> float:
    """
    Score document relevance to topic (0.0 - 1.0).
    Simple keyword overlap — fast and good enough at this scale.
    """
    if not doc.get("raw_text"):
        return 0.0

    topic_words = set(topic.lower().split())
    # Remove stop words
    stop_words = {"the", "a", "an", "of", "in", "for", "and", "or", "to", "is", "are"}
    topic_words -= stop_words

    text_lower = doc["raw_text"].lower()
    matches = sum(1 for word in topic_words if word in text_lower)
    score = matches / max(len(topic_words), 1)

    # Boost score if topic words appear in title
    title = (doc.get("title") or "").lower()
    title_matches = sum(1 for word in topic_words if word in title)
    title_boost = (title_matches / max(len(topic_words), 1)) * 0.3

    return min(1.0, score + title_boost)
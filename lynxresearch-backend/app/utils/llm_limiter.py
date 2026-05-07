# app/utils/llm_limiter.py
"""
Central LLM call wrapper — concurrency control, retry with exponential
backoff, and prompt truncation.  Applies to ALL Groq calls.
"""

import asyncio
import logging
import random
import time
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Global semaphore — strict concurrency cap for Groq calls.
_groq_semaphore = asyncio.Semaphore(max(1, settings.GROQ_MAX_CONCURRENT_CALLS))

# Track last call time for rate spacing
_last_groq_call: float = 0.0
_MIN_CALL_GAP_SECONDS = settings.GROQ_MIN_CALL_GAP_SECONDS


async def groq_call_with_retry(
    llm,
    messages: list,
    *,
    max_retries: int = 4,
    min_call_gap_seconds: float | None = None,
    label: str = "Groq",
) -> "AIMessage":
    """
    Invoke a Groq LLM with:
      - Semaphore (max 1 concurrent call)
      - Minimum gap between calls
      - Exponential backoff on 429/413/rate errors
      - Clear logging at each step
    """
    global _last_groq_call

    working_messages = list(messages)
    call_gap = _MIN_CALL_GAP_SECONDS if min_call_gap_seconds is None else max(0.0, min_call_gap_seconds)
    async with _groq_semaphore:
        last_error = None

        for attempt in range(max_retries):
            # Enforce minimum gap
            now = time.monotonic()
            elapsed = now - _last_groq_call
            if elapsed < call_gap:
                await asyncio.sleep(call_gap - elapsed)

            try:
                logger.info(f"[{label}] LLM call attempt {attempt + 1}/{max_retries}")
                _last_groq_call = time.monotonic()
                response = await llm.ainvoke(working_messages)
                logger.info(f"[{label}] LLM call succeeded")
                return response

            except Exception as e:
                last_error = e
                err_str = str(e).lower()

                # Retriable errors: 429 (rate), 413 (too large), 503 (overloaded)
                is_retriable = any(
                    x in err_str
                    for x in ["429", "413", "rate", "quota", "limit", "too large", "overloaded", "503"]
                )

                if is_retriable:
                    if "413" in err_str or "request too large" in err_str:
                        working_messages = shrink_messages_for_retry(working_messages, shrink_ratio=0.22)
                        logger.warning(
                            f"[{label}] Request too large, shrinking prompt. "
                            f"New estimate tokens={estimate_message_tokens(working_messages)}"
                        )
                    # Exponential backoff with small jitter to avoid synchronized retries.
                    base_wait = min(settings.GROQ_RETRY_BASE_SECONDS * (2 ** attempt), settings.GROQ_RETRY_MAX_SECONDS)
                    wait = base_wait + random.uniform(0, 1.0)
                    logger.warning(
                        f"[{label}] Retriable error (attempt {attempt + 1}): "
                        f"{str(e)[:120]}. Waiting {wait:.2f}s..."
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"[{label}] Non-retriable error: {e}", exc_info=True)
                    raise

        raise ValueError(
            f"[{label}] Failed after {max_retries} attempts. Last error: {last_error}"
        )


def estimate_message_tokens(messages: list) -> int:
    """Rough token estimate: 1 token ≈ 4 chars."""
    total_chars = 0
    for m in messages:
        content = getattr(m, "content", m)
        total_chars += len(str(content))
    return total_chars // 4


def trim_prompt_to_budget(text: str, max_tokens: int = 3000) -> str:
    """Hard-trim text to fit within a token budget."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...truncated to fit context limit...]"


def shrink_messages_for_retry(messages: list, shrink_ratio: float = 0.2) -> list:
    """
    Shrink the largest message payloads in-place to recover from 413/token overflow.
    """
    ratio = min(max(shrink_ratio, 0.05), 0.5)
    reduced = list(messages)
    for msg in reduced:
        content = getattr(msg, "content", None)
        if not content:
            continue
        text = str(content)
        if len(text) < 600:
            continue
        keep_chars = int(len(text) * (1.0 - ratio))
        msg.content = text[:keep_chars] + "\n\n[...auto-trimmed for token safety...]"
    return reduced

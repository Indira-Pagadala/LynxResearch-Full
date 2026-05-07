# app/utils/gemini_limiter.py

import asyncio
import time
import logging

logger = logging.getLogger(__name__)

_last_flash_call: float = 0.0
_flash_lock = asyncio.Lock()

_FLASH_DELAY_SECONDS = 5.0

SAFE_PRO_MODEL   = "gemini-2.0-flash"
SAFE_FLASH_MODEL = "gemini-2.0-flash"


def _get_flash_delay() -> float:
    try:
        from app.config import get_settings
        s = get_settings()
        return float(getattr(s, "GEMINI_FLASH_DELAY_SECONDS", _FLASH_DELAY_SECONDS))
    except Exception:
        return _FLASH_DELAY_SECONDS


async def gemini_flash_call(llm, messages_or_prompt):
    """
    Rate-limited wrapper for the single Gemini Flash call
    used in search query generation (1 call per run).
    """
    global _last_flash_call

    flash_delay = _get_flash_delay()

    async with _flash_lock:
        now     = time.monotonic()
        elapsed = now - _last_flash_call
        wait    = flash_delay - elapsed

        if wait > 0 and _last_flash_call > 0:
            logger.info(f"[GeminiLimiter] Flash pause {wait:.1f}s")
            await asyncio.sleep(wait)

        try:
            response         = await llm.ainvoke(messages_or_prompt)
            _last_flash_call = time.monotonic()
            return response
        except Exception as e:
            _last_flash_call = time.monotonic()
            err = str(e)
            if "429" in err or "ResourceExhausted" in err:
                logger.warning("[GeminiLimiter] Flash 429 — waiting 30s then retry")
                await asyncio.sleep(30)
                response         = await llm.ainvoke(messages_or_prompt)
                _last_flash_call = time.monotonic()
                return response
            raise


async def gemini_pro_call(llm, messages):
    """
    Backwards compat — routes through Groq author LLM now.
    """
    from app.utils.llm_factory import get_author_llm
    groq_llm = get_author_llm(temperature=0.4)
    return await groq_llm.ainvoke(messages)
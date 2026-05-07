# app/utils/llm_factory.py

import logging
from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


def get_author_llm(temperature: float = 0.4):
    """
    Returns Groq LLM for report authoring.
    Lazy import inside function — prevents metaclass conflict
    with langchain-google-genai at module load time.
    Free tier: 14,400 requests/day, no daily token cap.
    """
    if not settings.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set in .env. "
            "Get a free key at https://console.groq.com"
        )

    model = settings.GROQ_AUTHOR_MODEL or "llama-3.3-70b-versatile"
    # Hard cap to avoid single request exceeding free-tier TPM limits.
    max_tokens = min(int(settings.MAX_TOKENS_PER_AUTHOR), 3600)
    logger.info(f"[LLMFactory] Author LLM → Groq / {model}")

    from langchain_groq import ChatGroq
    return ChatGroq(
        model=model,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_rag_llm(temperature: float = 0.2):
    """
    Returns Groq LLM for RAG chat.
    Uses smaller faster model for low latency responses.
    """
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env")

    model = settings.GROQ_RAG_MODEL or "llama-3.1-8b-instant"
    logger.info(f"[LLMFactory] RAG LLM → Groq / {model}")

    from langchain_groq import ChatGroq
    return ChatGroq(
        model=model,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
        max_tokens=1500,
    )


def get_flash_llm(temperature: float = 0.1):
    """
    Returns Gemini Flash LLM.
    Used ONLY for search query generation — 1 call per research run.
    Lazy import inside function — prevents metaclass conflict
    with langchain-groq at module load time.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_NANO_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,
    )
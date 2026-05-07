# app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────
    APP_ENV: str = Field(default="development")
    SECRET_KEY: str = Field(default="changeme-in-production")

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/lynxresearch"
    )

    # ── Google Gemini ─────────────────────────────────────────
    # Only used for search query generation — 1 call per run
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_NANO_MODEL: str = Field(default="gemini-2.0-flash")

    # Gemini rate limit (for that 1 search query call)
    GEMINI_FLASH_DELAY_SECONDS: float = Field(default=5.0)
    # Keep this for backwards compat with limiter
    GEMINI_PRO_DELAY_SECONDS: float = Field(default=35.0)

    # ── Groq ──────────────────────────────────────────────────
    # All authoring + RAG runs on Groq
    # Free: 14,400 req/day, 6000 tokens/min, no daily token cap
    GROQ_API_KEY: str = Field(default="")
    GROQ_AUTHOR_MODEL: str = Field(default="llama-3.3-70b-versatile")
    GROQ_RAG_MODEL: str = Field(default="llama-3.1-8b-instant")
    GROQ_MAX_CONCURRENT_CALLS: int = Field(default=1)
    GROQ_MIN_CALL_GAP_SECONDS: float = Field(default=2.0)
    GROQ_RETRY_BASE_SECONDS: float = Field(default=3.0)
    GROQ_RETRY_MAX_SECONDS: float = Field(default=45.0)

    # ── Pipeline reliability ──────────────────────────────────
    PIPELINE_MAX_CONCURRENT_RUNS: int = Field(default=1)
    LOG_DIR: Path = Field(default=Path("./logs"))

    # ── Tavily Search ─────────────────────────────────────────
    TAVILY_API_KEY: str = Field(default="")

    # ── Qdrant ────────────────────────────────────────────────
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str = Field(default="")
    QDRANT_COLLECTION: str = Field(default="lynxresearch")

    # ── File Storage ──────────────────────────────────────────
    REPORTS_DIR: Path = Field(default=Path("./reports"))
    CHARTS_DIR: Path = Field(default=Path("./charts"))

    # ── Crawling ──────────────────────────────────────────────
    MAX_URLS_TO_CRAWL: int = Field(default=60)
    CRAWL_BATCH_SIZE: int = Field(default=10)
    CRAWL_TIMEOUT_SECONDS: int = Field(default=15)

    # ── LLM ───────────────────────────────────────────────────
    MAX_TOKENS_PER_AUTHOR: int = Field(default=8000)

    # ── Chunking ──────────────────────────────────────────────
    CHUNK_SIZE: int = Field(default=800)
    CHUNK_OVERLAP: int = Field(default=100)

    # ── Forecasting ───────────────────────────────────────────
    FORECAST_YEARS: int = Field(default=5)
    MAX_TIMESERIES_TO_MODEL: int = Field(default=3)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
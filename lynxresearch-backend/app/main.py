# app/main.py

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.database import init_db, close_db
from app.services.qdrant_service import ensure_collection_exists
from app.api import runs, reports, chat, workspaces
from app.config import get_settings
settings = get_settings()

# ── Logging setup ─────────────────────────────────────────────
# Clear existing handlers to prevent duplication on uvicorn reload
root_logger = logging.getLogger()
if root_logger.handlers:
    root_logger.handlers.clear()

log_dir = Path(settings.LOG_DIR)
log_dir.mkdir(parents=True, exist_ok=True)
app_log_path = log_dir / "app.log"
formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
file_handler = logging.FileHandler(app_log_path, mode="a", encoding="utf-8")
file_handler.setFormatter(formatter)
root_logger.setLevel(logging.INFO)
root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)

# Silence SQLAlchemy engine noise — it doubles every line
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ── Lifespan (startup + shutdown) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    Creates DB tables, Qdrant collection, report/charts dirs.
    """
    logger.info("🚀 LynxResearch backend starting up...")

    # Initialize DB
    await init_db()

    # Clean up orphaned runs (stuck in "running" from previous restart)
    await _cleanup_orphaned_runs()

    # Initialize Qdrant collection
    await ensure_collection_exists()

    # Ensure output directories exist
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("✅ All services initialized. Ready to receive requests.")

    yield  # App runs here

    logger.info("🛑 LynxResearch backend shutting down...")
    await close_db()
    logger.info("✅ Shutdown complete.")


async def _cleanup_orphaned_runs():
    """Mark any runs left in 'running'/'pending' as 'failed' on startup."""
    from app.database import AsyncSessionLocal
    from app.models.run import ResearchRun
    from sqlalchemy import update

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(ResearchRun)
            .where(ResearchRun.status.in_(["running", "pending"]))
            .values(status="failed", error_message="Server restarted during execution", current_stage="failed")
        )
        await db.commit()
        if result.rowcount > 0:
            logger.warning(f"⚠️  Cleaned up {result.rowcount} orphaned run(s) from previous session")


# ── App Factory ───────────────────────────────────────────────
app = FastAPI(
    title="LynxResearch API",
    description="Autonomous Multi-Agent Research Report Generator",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production: restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ───────────────────────────────────────────────────
app.include_router(runs.router)
app.include_router(reports.router)
app.include_router(chat.router)
app.include_router(workspaces.router)


# ── Health Check ──────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "LynxResearch API",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "LynxResearch API",
        "docs": "/docs",
        "health": "/health",
    }
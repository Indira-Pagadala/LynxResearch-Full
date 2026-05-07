# app/database.py

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    """
    All ORM models inherit from this Base.
    """
    pass


# ── Engine ────────────────────────────────────────────────────────────────────
async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.APP_ENV == "development"),   # Log SQL only in dev
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,                          # Reconnect on stale connections
    pool_recycle=3600,                           # Recycle connections every hour
)
engine = async_engine  # Alias for backward compatibility

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,     # Important: keeps objects accessible after commit
    autoflush=False,
    autocommit=False,
)


# ── Dependency for FastAPI routes ─────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """
    FastAPI dependency. Use in route functions like:
    async def my_route(db: AsyncSession = Depends(get_db)):
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Startup / Shutdown helpers ────────────────────────────────────────────────
async def init_db():
    """
    Called on app startup. Creates all tables if they don't exist.
    In production, rely on Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database initialized")


async def close_db():
    """Called on app shutdown."""
    await engine.dispose()
    logger.info("✅ Database connection closed")
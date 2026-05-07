"""Add workspaces table and workspace_id to research_runs

Run this migration:
    python -m app.migrations.add_workspaces
"""

import asyncio
import logging
from sqlalchemy import text
from app.database import async_engine

logger = logging.getLogger(__name__)


async def migrate():
    async with async_engine.begin() as conn:
        # Create workspaces table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(200) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_workspaces_user_id ON workspaces(user_id);
        """))

        # Add workspace_id column to research_runs if it doesn't exist
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'research_runs' AND column_name = 'workspace_id';
        """))
        if not result.fetchone():
            await conn.execute(text("""
                ALTER TABLE research_runs
                ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL;
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_runs_workspace_id ON research_runs(workspace_id);
            """))
            logger.info("✅ Added workspace_id column to research_runs")
        else:
            logger.info("ℹ️  workspace_id column already exists")

        logger.info("✅ Workspaces migration complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(migrate())

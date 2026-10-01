"""Database initialization and connection management using aiosqlite."""
from __future__ import annotations

import aiosqlite
from pathlib import Path

from src.config import DB_PATH


async def init_db(db_path: Path | str = DB_PATH) -> None:
    """Initialize database tables for user quota tracking."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(path)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_daily_usage (
                user_id INTEGER NOT NULL,
                usage_date TEXT NOT NULL,
                used_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, usage_date)
            );
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_date ON user_daily_usage(user_id, usage_date);
        """)
        await db.commit()

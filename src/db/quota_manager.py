"""Daily quota management with atomic SQLite transactions."""
from __future__ import annotations

import datetime
from pathlib import Path
import aiosqlite

from src.config import DAILY_FREE_LIMIT, DB_PATH, TIMEZONE_OFFSET_HOURS


class QuotaManager:
    """Manages daily free user quotas and usage counts."""

    @staticmethod
    def get_current_date_str() -> str:
        """Return the current date string (YYYY-MM-DD) based on configured timezone offset."""
        tz = datetime.timezone(datetime.timedelta(hours=TIMEZONE_OFFSET_HOURS))
        now = datetime.datetime.now(tz)
        return now.strftime("%Y-%m-%d")

    @classmethod
    async def get_user_quota(
        cls,
        user_id: int,
        db_path: Path | str = DB_PATH,
        daily_limit: int = DAILY_FREE_LIMIT,
    ) -> tuple[int, int]:
        """
        Returns (used_count, remaining_quota) for the given user today.
        """
        date_str = cls.get_current_date_str()
        async with aiosqlite.connect(str(db_path)) as db:
            async with db.execute(
                "SELECT used_count FROM user_daily_usage WHERE user_id = ? AND usage_date = ?",
                (user_id, date_str),
            ) as cursor:
                row = await cursor.fetchone()
                used = row[0] if row else 0
                remaining = max(0, daily_limit - used)
                return used, remaining

    @classmethod
    async def check_and_consume_quota(
        cls,
        user_id: int,
        db_path: Path | str = DB_PATH,
        daily_limit: int = DAILY_FREE_LIMIT,
    ) -> tuple[bool, int, int]:
        """
        Check if user has remaining quota today. If yes, increment used_count by 1.
        Returns:
            (allowed: bool, new_used_count: int, new_remaining_quota: int)
        """
        date_str = cls.get_current_date_str()
        async with aiosqlite.connect(str(db_path)) as db:
            await db.execute("BEGIN IMMEDIATE")
            try:
                async with db.execute(
                    "SELECT used_count FROM user_daily_usage WHERE user_id = ? AND usage_date = ?",
                    (user_id, date_str),
                ) as cursor:
                    row = await cursor.fetchone()
                    used = row[0] if row else 0

                if used >= daily_limit:
                    await db.rollback()
                    return False, used, 0

                new_used = used + 1
                await db.execute("""
                    INSERT INTO user_daily_usage (user_id, usage_date, used_count, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, usage_date) DO UPDATE SET
                        used_count = excluded.used_count,
                        updated_at = CURRENT_TIMESTAMP
                """, (user_id, date_str, new_used))
                await db.commit()

                remaining = max(0, daily_limit - new_used)
                return True, new_used, remaining

            except Exception:
                await db.rollback()
                raise

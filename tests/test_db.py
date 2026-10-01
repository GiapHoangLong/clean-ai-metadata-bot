"""Unit tests for SQLite QuotaManager."""
from __future__ import annotations

from pathlib import Path
import pytest

from src.db.database import init_db
from src.db.quota_manager import QuotaManager


@pytest.mark.asyncio
async def test_quota_initial_state(tmp_path: Path) -> None:
    db_file = tmp_path / "test_bot.db"
    await init_db(db_file)

    used, remaining = await QuotaManager.get_user_quota(user_id=12345, db_path=db_file, daily_limit=50)
    assert used == 0
    assert remaining == 50


@pytest.mark.asyncio
async def test_quota_consumption_up_to_50(tmp_path: Path) -> None:
    db_file = tmp_path / "test_bot.db"
    await init_db(db_file)
    user_id = 99999

    # Consume 49 times
    for i in range(1, 50):
        allowed, used, remaining = await QuotaManager.check_and_consume_quota(
            user_id=user_id, db_path=db_file, daily_limit=50
        )
        assert allowed is True
        assert used == i
        assert remaining == 50 - i

    # 50th time
    allowed, used, remaining = await QuotaManager.check_and_consume_quota(
        user_id=user_id, db_path=db_file, daily_limit=50
    )
    assert allowed is True
    assert used == 50
    assert remaining == 0

    # 51st time: Must be rejected!
    allowed, used, remaining = await QuotaManager.check_and_consume_quota(
        user_id=user_id, db_path=db_file, daily_limit=50
    )
    assert allowed is False
    assert used == 50
    assert remaining == 0

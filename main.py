"""Main entry point for CleanAI Metadata Stripper Bot."""
from __future__ import annotations

import asyncio
import logging
import sys

# Safe UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.bot.bot import build_application
from src.config import DAILY_FREE_LIMIT, TELEGRAM_BOT_TOKEN
from src.db.database import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("CleanAI-Bot")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "TELEGRAM_BOT_TOKEN is empty! Please set your token in .env file (see .env.example)."
        )
        print("\n[!] LỖI: Chưa cấu hình TELEGRAM_BOT_TOKEN!")
        print("Vui lòng tạo file .env từ .env.example và điền token nhận từ @BotFather.\n")
        sys.exit(1)

    print("=" * 60)
    print("🚀 Đang khởi động CleanAI Metadata Stripper Bot...")
    print(f"🆓 Hạn mức miễn phí: {DAILY_FREE_LIMIT} lượt/ngày/user")
    print("=" * 60)

    # Initialize SQLite database schema
    asyncio.run(init_db())

    # Build and run application
    app = build_application(TELEGRAM_BOT_TOKEN)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

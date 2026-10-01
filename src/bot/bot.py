"""Telegram Bot setup and application assembly."""
from __future__ import annotations

import logging
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.bot.handlers import (
    help_handler,
    process_media_handler,
    quota_handler,
    start_handler,
)
from src.config import TELEGRAM_BOT_TOKEN
from src.db.database import init_db

logger = logging.getLogger(__name__)


def build_application(token: str = TELEGRAM_BOT_TOKEN) -> Application:
    """Build and configure the Telegram Bot Application."""
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot will not be able to connect.")

    app = ApplicationBuilder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("quota", quota_handler))

    # Media handlers
    # 1. Photos
    app.add_handler(MessageHandler(filters.PHOTO, process_media_handler))

    # 2. Videos (MP4, MOV, etc.)
    app.add_handler(MessageHandler(filters.VIDEO, process_media_handler))

    # 3. Documents (Images or Videos sent as uncompressed file)
    app.add_handler(MessageHandler(filters.Document.IMAGE, process_media_handler))
    app.add_handler(MessageHandler(filters.Document.VIDEO, process_media_handler))
    app.add_handler(
        MessageHandler(
            filters.Document.FileExtension("jpg")
            | filters.Document.FileExtension("jpeg")
            | filters.Document.FileExtension("png")
            | filters.Document.FileExtension("webp")
            | filters.Document.FileExtension("mp4")
            | filters.Document.FileExtension("mov")
            | filters.Document.FileExtension("webm")
            | filters.Document.FileExtension("mkv")
            | filters.Document.FileExtension("avi"),
            process_media_handler,
        )
    )

    return app


async def run_bot() -> None:
    """Initialize resources and start polling."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    # Initialize SQLite database
    await init_db()

    app = build_application()
    logger.info("Starting CleanAI Metadata Telegram Bot polling...")
    await app.run_polling()

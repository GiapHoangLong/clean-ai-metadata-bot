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

import asyncio
import os

logger = logging.getLogger(__name__)


async def _post_init(app: Application) -> None:
    """Post-initialization hook for database and optional PaaS health-check server."""
    await init_db()

    port_str = os.getenv("PORT")
    if port_str:
        try:
            port = int(port_str)

            async def handle_client(
                reader: asyncio.StreamReader, writer: asyncio.StreamWriter
            ) -> None:
                try:
                    await reader.read(1024)
                    body = b"OK - CleanAI Telegram Bot is active\n"
                    response = (
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: text/plain; charset=utf-8\r\n"
                        + f"Content-Length: {len(body)}\r\n".encode("ascii")
                        + b"Connection: close\r\n\r\n"
                        + body
                    )
                    writer.write(response)
                    await writer.drain()
                except Exception:
                    pass
                finally:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass

            server = await asyncio.start_server(handle_client, "0.0.0.0", port)
            app.bot_data["health_server"] = server
            logger.info("PaaS health-check HTTP server listening on port %d", port)

            # Start keep-alive loop to prevent Render Free tier from sleeping after 15 minutes
            ext_url = os.getenv("RENDER_EXTERNAL_URL", "https://clean-ai-metadata-bot.onrender.com")

            async def _keep_alive_loop() -> None:
                import httpx

                await asyncio.sleep(60)
                async with httpx.AsyncClient() as client:
                    while True:
                        try:
                            resp = await client.get(ext_url, timeout=15.0)
                            logger.info("Keep-alive ping to %s: %d", ext_url, resp.status_code)
                        except Exception as ping_err:
                            logger.debug("Keep-alive ping note: %s", ping_err)
                        await asyncio.sleep(600)  # Ping every 10 minutes

            app.bot_data["keep_alive_task"] = asyncio.create_task(_keep_alive_loop())
        except Exception as exc:
            logger.warning("Could not start PaaS health-check server on port %s: %s", port_str, exc)


def build_application(token: str = TELEGRAM_BOT_TOKEN) -> Application:
    """Build and configure the Telegram Bot Application."""
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot will not be able to connect.")

    app = ApplicationBuilder().token(token).post_init(_post_init).build()

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

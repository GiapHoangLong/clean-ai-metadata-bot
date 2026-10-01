"""Configuration settings for CleanAI Metadata Stripper Bot."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Telegram Settings
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Quota Settings (User requested: 50 free usages/day)
DAILY_FREE_LIMIT: int = int(os.getenv("DAILY_FREE_LIMIT", "50"))
TIMEZONE_OFFSET_HOURS: int = int(os.getenv("TIMEZONE_OFFSET_HOURS", "7"))  # UTC+7 Vietnam

# Storage Paths
DB_PATH: Path = BASE_DIR / os.getenv("DB_PATH", "data/bot.db")
TEMP_DIR: Path = BASE_DIR / os.getenv("TEMP_DIR", "scratch/temp_uploads")
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

# Ensure required directories exist
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

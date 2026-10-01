"""Safe temporary file management and cleanup utilities."""
from __future__ import annotations

import contextlib
import os
import shutil
import uuid
from pathlib import Path
from typing import AsyncGenerator

from src.config import TEMP_DIR


@contextlib.asynccontextmanager
async def temporary_processing_directory(
    session_id: str | None = None,
    base_dir: Path | str = TEMP_DIR,
) -> AsyncGenerator[Path, None]:
    """
    Context manager that creates a unique temporary working directory
    and guarantees it is completely purged when exiting the context.
    """
    token = session_id or str(uuid.uuid4())
    work_dir = Path(base_dir) / f"session_{token}"
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        yield work_dir
    finally:
        try:
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def purge_old_scratch_files(base_dir: Path | str = TEMP_DIR, max_age_seconds: int = 3600) -> int:
    """Purge temporary files older than max_age_seconds."""
    path = Path(base_dir)
    if not path.exists():
        return 0

    import time
    now = time.time()
    purged = 0

    for item in path.iterdir():
        try:
            mtime = item.stat().st_mtime
            if now - mtime > max_age_seconds:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
                purged += 1
        except Exception:
            pass

    return purged

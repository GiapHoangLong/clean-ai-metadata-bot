"""Lossless Video Metadata Stripper using direct stream copy (Zero re-encoding)."""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from src.engine.models import ImageFormat, StripResult


class VideoStripper:
    """Strips container metadata, QuickTime atoms, C2PA, and AI tags from MP4, MOV, WEBM, MKV."""

    SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}

    @classmethod
    def is_video(cls, path_or_name: str | Path) -> bool:
        ext = Path(path_or_name).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def strip_video(cls, input_path: str | Path, output_path: str | Path) -> StripResult:
        in_path = Path(input_path)
        out_path = Path(output_path)
        size_before = in_path.stat().st_size

        # Check for ffmpeg
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            return StripResult(
                format=ImageFormat.UNKNOWN,
                input_path=in_path,
                output_path=out_path,
                size_before=size_before,
                size_after=0,
                dropped_tags=[],
                is_lossless=False,
                success=False,
                error_message="ffmpeg không khả dụng trên hệ thống",
            )

        # Lossless stream copy command:
        # -map_metadata -1 : Clear all global, stream, and chapter metadata
        # -c copy          : Copy video & audio streams directly (0 re-encoding, 100% lossless)
        # -dn              : Drop data streams (removes hidden GPS/proprietary tracking streams)
        # -movflags faststart : Optimizes MP4 for fast streaming playback
        ext = in_path.suffix.lower()
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(in_path),
            "-map_metadata", "-1",
            "-c", "copy",
            "-dn",
        ]

        if ext in (".mp4", ".mov"):
            cmd.extend(["-movflags", "+faststart"])

        cmd.append(str(out_path))

        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )

            if process.returncode != 0 or not out_path.exists():
                err_msg = process.stderr.decode("utf-8", errors="ignore")
                return StripResult(
                    format=ImageFormat.UNKNOWN,
                    input_path=in_path,
                    output_path=out_path,
                    size_before=size_before,
                    size_after=0,
                    dropped_tags=[],
                    is_lossless=False,
                    success=False,
                    error_message=f"Lỗi xử lý video: {err_msg[:200]}",
                )

            size_after = out_path.stat().st_size
            dropped_tags = ["Video Container Metadata", "AI Generation Atoms", "Stream Tags"]

            return StripResult(
                format=ImageFormat.UNKNOWN,
                input_path=in_path,
                output_path=out_path,
                size_before=size_before,
                size_after=size_after,
                dropped_tags=dropped_tags,
                is_lossless=True,
                success=True,
            )

        except Exception as e:
            return StripResult(
                format=ImageFormat.UNKNOWN,
                input_path=in_path,
                output_path=out_path,
                size_before=size_before,
                size_after=0,
                dropped_tags=[],
                is_lossless=False,
                success=False,
                error_message=str(e),
            )

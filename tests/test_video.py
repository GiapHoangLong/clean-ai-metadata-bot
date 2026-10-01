"""Tests for Video metadata stripping using VideoStripper."""
from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
import pytest

from src.engine.video_stripper import VideoStripper


def test_video_stripper_lossless(tmp_path: Path) -> None:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        pytest.skip("ffmpeg not available in environment")

    raw_mp4 = tmp_path / "ai_video.mp4"
    clean_mp4 = tmp_path / "clean_ai_video.mp4"

    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=1:size=64x64:rate=1",
        "-metadata", "title=Runway Gen-3 Alpha Test",
        "-metadata", "comment=Prompt: cinematic cyberpunk scene 4k",
        "-metadata", "artist=AI Generator",
        str(raw_mp4),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    assert raw_mp4.exists()
    assert raw_mp4.stat().st_size > 0

    result = VideoStripper.strip_video(raw_mp4, clean_mp4)
    assert result.success is True
    assert result.is_lossless is True
    assert clean_mp4.exists()
    assert clean_mp4.stat().st_size > 0

    ffprobe_bin = shutil.which("ffprobe")
    if ffprobe_bin:
        probe_cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries", "format_tags",
            "-of", "default=noprint_wrappers=1",
            str(clean_mp4),
        ]
        out = subprocess.check_output(probe_cmd).decode("utf-8")
        assert "Runway" not in out
        assert "cyberpunk" not in out

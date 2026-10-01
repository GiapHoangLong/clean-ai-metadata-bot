"""Data models for AI Metadata Stripper Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ImageFormat(str, Enum):
    PNG = "PNG"
    JPEG = "JPEG"
    WEBP = "WEBP"
    UNKNOWN = "UNKNOWN"


@dataclass
class InspectionResult:
    """Detailed inspection of metadata present in the original file."""
    format: ImageFormat
    size_bytes: int
    has_exif: bool = False
    has_xmp: bool = False
    has_c2pa: bool = False
    has_iptc: bool = False
    has_icc: bool = False
    has_comfyui_workflow: bool = False
    has_sd_parameters: bool = False
    has_midjourney_meta: bool = False
    ai_signatures: list[str] = field(default_factory=list)
    detected_tags: list[str] = field(default_factory=list)

    @property
    def has_any_metadata(self) -> bool:
        return bool(self.detected_tags or self.ai_signatures or self.has_exif or self.has_xmp or self.has_c2pa or self.has_icc)


@dataclass
class StripResult:
    """Result of metadata stripping operation."""
    format: ImageFormat
    input_path: Path
    output_path: Path
    size_before: int
    size_after: int
    dropped_tags: list[str] = field(default_factory=list)
    is_lossless: bool = True
    success: bool = True
    error_message: str | None = None

    @property
    def size_before_kb(self) -> float:
        return self.size_before / 1024.0

    @property
    def size_after_kb(self) -> float:
        return self.size_after / 1024.0

    @property
    def diff_bytes(self) -> int:
        return self.size_after - self.size_before

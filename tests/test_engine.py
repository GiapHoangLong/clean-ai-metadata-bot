"""Unit and integration tests for AI metadata detection and stripping."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import pytest
from PIL import Image

from src.engine.binary_stripper import BinaryStripper
from src.engine.inspector import MetadataInspector
from src.engine.models import ImageFormat
from tests.create_samples import (
    create_sample_jpeg_with_ai_metadata,
    create_sample_png_with_ai_metadata,
    create_sample_webp_with_metadata,
)


@pytest.fixture
def temp_sample_dir(tmp_path: Path) -> Path:
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir()
    return sample_dir


def test_png_ai_metadata_detection_and_strip(temp_sample_dir: Path) -> None:
    raw_png = temp_sample_dir / "test_sd.png"
    clean_png = temp_sample_dir / "clean_test_sd.png"
    create_sample_png_with_ai_metadata(raw_png)

    inspection = MetadataInspector.inspect_file(raw_png)
    assert inspection.format == ImageFormat.PNG
    assert inspection.has_comfyui_workflow is True or inspection.has_sd_parameters is True

    with Image.open(raw_png) as img:
        orig_pixels = img.tobytes()
        orig_size = img.size
        orig_mode = img.mode

    result = BinaryStripper.strip_file(raw_png, clean_png)
    assert result.success is True
    assert result.is_lossless is True
    assert clean_png.exists()
    assert result.size_after < result.size_before

    post_inspection = MetadataInspector.inspect_file(clean_png)
    assert post_inspection.has_sd_parameters is False
    assert post_inspection.has_comfyui_workflow is False
    assert post_inspection.has_exif is False
    assert post_inspection.has_xmp is False
    assert post_inspection.has_c2pa is False
    assert len(post_inspection.detected_tags) == 0

    with Image.open(clean_png) as clean_img:
        assert clean_img.size == orig_size
        assert clean_img.mode == orig_mode
        assert clean_img.tobytes() == orig_pixels


def test_jpeg_ai_metadata_detection_and_strip(temp_sample_dir: Path) -> None:
    raw_jpg = temp_sample_dir / "test_ai.jpg"
    clean_jpg = temp_sample_dir / "clean_test_ai.jpg"
    create_sample_jpeg_with_ai_metadata(raw_jpg)

    inspection = MetadataInspector.inspect_file(raw_jpg)
    assert inspection.format == ImageFormat.JPEG
    assert inspection.has_exif is True
    assert inspection.has_xmp is True
    assert inspection.has_c2pa is True
    assert inspection.has_iptc is True

    result = BinaryStripper.strip_file(raw_jpg, clean_jpg)
    assert result.success is True
    assert result.is_lossless is True
    assert clean_jpg.exists()
    assert result.size_after < result.size_before

    post_inspection = MetadataInspector.inspect_file(clean_jpg)
    assert post_inspection.has_exif is False
    assert post_inspection.has_xmp is False
    assert post_inspection.has_c2pa is False
    assert post_inspection.has_iptc is False
    assert post_inspection.has_icc is False
    assert len(post_inspection.detected_tags) == 0

    with Image.open(clean_jpg) as img:
        img.verify()


def test_webp_metadata_detection_and_strip(temp_sample_dir: Path) -> None:
    raw_webp = temp_sample_dir / "test.webp"
    clean_webp = temp_sample_dir / "clean_test.webp"
    create_sample_webp_with_metadata(raw_webp)

    result = BinaryStripper.strip_file(raw_webp, clean_webp)
    assert result.success is True
    assert clean_webp.exists()

    post_inspection = MetadataInspector.inspect_file(clean_webp)
    assert post_inspection.has_exif is False
    assert post_inspection.has_xmp is False

    with Image.open(clean_webp) as img:
        img.verify()

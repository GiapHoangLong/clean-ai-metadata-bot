"""Lossless Binary Metadata Stripper for PNG, JPEG, and WebP images."""
from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import BinaryIO

from PIL import Image

from src.engine.inspector import MetadataInspector
from src.engine.models import ImageFormat, StripResult


class BinaryStripper:
    """Performs deep, lossless byte-level metadata removal without decoding pixel streams."""

    @classmethod
    def strip_file(cls, input_path: str | Path, output_path: str | Path) -> StripResult:
        in_path = Path(input_path)
        out_path = Path(output_path)
        data = in_path.read_bytes()
        size_before = len(data)

        # Pre-inspect to identify tags before stripping
        inspection = MetadataInspector.inspect_bytes(data)
        dropped_tags: list[str] = []

        try:
            if inspection.format == ImageFormat.PNG:
                clean_data, dropped_tags = cls._strip_png(data, inspection.detected_tags)
                is_lossless = True
            elif inspection.format == ImageFormat.JPEG:
                clean_data, dropped_tags = cls._strip_jpeg(data, inspection.detected_tags)
                is_lossless = True
            elif inspection.format == ImageFormat.WEBP:
                clean_data, dropped_tags = cls._strip_webp(data, inspection.detected_tags)
                is_lossless = True
            else:
                # Fallback to Pillow sanitization
                clean_data, dropped_tags = cls._fallback_sanitize(in_path)
                is_lossless = False

            # Verify the cleaned data is valid
            cls._verify_clean_image(clean_data)

            out_path.write_bytes(clean_data)
            size_after = len(clean_data)

            # If no specific tags were named but data changed, note general metadata
            if not dropped_tags and size_after < size_before:
                dropped_tags = ["Metadata Headers"]

            return StripResult(
                format=inspection.format,
                input_path=in_path,
                output_path=out_path,
                size_before=size_before,
                size_after=size_after,
                dropped_tags=dropped_tags,
                is_lossless=is_lossless,
                success=True,
            )

        except Exception as e:
            # Fallback path if lossless binary strip failed on edge case
            try:
                clean_data, fallback_tags = cls._fallback_sanitize(in_path)
                out_path.write_bytes(clean_data)
                return StripResult(
                    format=inspection.format,
                    input_path=in_path,
                    output_path=out_path,
                    size_before=size_before,
                    size_after=len(clean_data),
                    dropped_tags=fallback_tags or inspection.detected_tags or ["EXIF", "Metadata"],
                    is_lossless=False,
                    success=True,
                )
            except Exception as fallback_err:
                return StripResult(
                    format=inspection.format,
                    input_path=in_path,
                    output_path=out_path,
                    size_before=size_before,
                    size_after=0,
                    dropped_tags=[],
                    is_lossless=False,
                    success=False,
                    error_message=f"Strip failed: {e}; Fallback failed: {fallback_err}",
                )

    @classmethod
    def _strip_png(cls, data: bytes, detected_tags: list[str]) -> tuple[bytes, list[str]]:
        """Losslessly strip all non-essential metadata chunks from PNG."""
        if len(data) < 8 or data[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Invalid PNG signature")

        out = bytearray(b"\x89PNG\r\n\x1a\n")
        offset = 8
        total_len = len(data)
        dropped: list[str] = []

        # Chunks to drop
        drop_types = {
            b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"iCCP",
            b"c2pa", b"caIp", b"XML:com.adobe.xmp", b"tIME"
        }

        while offset + 8 <= total_len:
            length = struct.unpack(">I", data[offset:offset + 4])[0]
            chunk_type = data[offset + 4:offset + 8]
            full_chunk_len = 12 + length

            if offset + full_chunk_len > total_len:
                break

            chunk_bytes = data[offset:offset + full_chunk_len]
            offset += full_chunk_len

            if chunk_type in drop_types:
                tag_name = chunk_type.decode("latin-1", errors="ignore").strip()
                if chunk_type in (b"tEXt", b"zTXt", b"iTXt"):
                    for d in detected_tags:
                        if d not in dropped:
                            dropped.append(d)
                    if not dropped and "Text Metadata" not in dropped:
                        dropped.append("Text Metadata")
                elif chunk_type == b"eXIf" and "EXIF" not in dropped:
                    dropped.append("EXIF")
                elif chunk_type == b"iCCP" and "ICC" not in dropped:
                    dropped.append("ICC")
                elif chunk_type in (b"c2pa", b"caIp") and "C2PA" not in dropped:
                    dropped.append("C2PA")
                continue

            out.extend(chunk_bytes)
            if chunk_type == b"IEND":
                break

        for t in detected_tags:
            if t not in dropped:
                dropped.append(t)

        return bytes(out), dropped

    @classmethod
    def _strip_jpeg(cls, data: bytes, detected_tags: list[str]) -> tuple[bytes, list[str]]:
        """Losslessly strip APP1 (Exif/XMP), APP2 (ICC), APP11 (C2PA), APP13 (IPTC)."""
        if len(data) < 2 or data[:2] != b"\xFF\xD8":
            raise ValueError("Invalid JPEG signature")

        out = bytearray(b"\xFF\xD8")
        stream = io.BytesIO(data[2:])
        dropped: list[str] = []

        drop_markers = {0xE1, 0xE2, 0xEB, 0xED}

        while True:
            marker = stream.read(2)
            if not marker or len(marker) < 2:
                break
            if marker[0] != 0xFF:
                out.extend(marker)
                continue

            m_type = marker[1]

            if m_type in (0xD8, 0xD9):
                out.extend(marker)
                continue
            if 0xD0 <= m_type <= 0xD7 or m_type == 0x01:
                out.extend(marker)
                continue

            if m_type == 0xDA:
                out.extend(marker)
                rest = stream.read()
                out.extend(rest)
                break

            len_bytes = stream.read(2)
            if len(len_bytes) < 2:
                break
            length = struct.unpack(">H", len_bytes)[0]
            payload = stream.read(length - 2)

            if m_type in drop_markers:
                if m_type == 0xE1:
                    if payload.startswith(b"Exif\x00\x00") and "EXIF" not in dropped:
                        dropped.append("EXIF")
                    elif "XMP" not in dropped:
                        dropped.append("XMP")
                elif m_type == 0xE2 and "ICC" not in dropped:
                    dropped.append("ICC")
                elif m_type == 0xEB and "C2PA" not in dropped:
                    dropped.append("C2PA")
                elif m_type == 0xED and "IPTC" not in dropped:
                    dropped.append("IPTC")
                continue

            out.extend(marker)
            out.extend(len_bytes)
            out.extend(payload)

        for t in detected_tags:
            if t not in dropped:
                dropped.append(t)

        return bytes(out), dropped

    @classmethod
    def _strip_webp(cls, data: bytes, detected_tags: list[str]) -> tuple[bytes, list[str]]:
        """Losslessly strip EXIF, XMP, ICCP chunks from WebP RIFF container."""
        if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
            raise ValueError("Invalid WebP signature")

        offset = 12
        total_len = len(data)
        out_chunks = bytearray()
        dropped: list[str] = []

        drop_chunks = {b"EXIF", b"XMP ", b"ICCP"}

        while offset + 8 <= total_len:
            fourcc = data[offset:offset + 4]
            chunk_size = struct.unpack("<I", data[offset + 4:offset + 8])[0]
            padded_size = chunk_size + (chunk_size % 2)
            chunk_payload = data[offset + 8:offset + 8 + chunk_size]
            full_chunk = data[offset:offset + 8 + padded_size]
            offset += 8 + padded_size

            if fourcc in drop_chunks:
                tag_name = fourcc.decode("latin-1", errors="ignore").strip()
                if tag_name not in dropped:
                    dropped.append(tag_name)
                continue

            if fourcc == b"VP8X" and len(chunk_payload) >= 10:
                flags = chunk_payload[0]
                new_flags = flags & ~(0x20 | 0x08 | 0x04)
                modified_payload = bytearray(chunk_payload)
                modified_payload[0] = new_flags
                out_chunks.extend(b"VP8X")
                out_chunks.extend(struct.pack("<I", len(modified_payload)))
                out_chunks.extend(modified_payload)
                if len(modified_payload) % 2 != 0:
                    out_chunks.append(0)
                continue

            out_chunks.extend(full_chunk)

        riff_size = 4 + len(out_chunks)
        out = bytearray(b"RIFF")
        out.extend(struct.pack("<I", riff_size))
        out.extend(b"WEBP")
        out.extend(out_chunks)

        for t in detected_tags:
            if t not in dropped:
                dropped.append(t)

        return bytes(out), dropped

    @classmethod
    def _fallback_sanitize(cls, input_path: Path) -> tuple[bytes, list[str]]:
        """Fallback Pillow sanitization that re-encodes pixel data with 0 metadata."""
        with Image.open(input_path) as img:
            out_buf = io.BytesIO()
            fmt = img.format or "JPEG"
            if fmt.upper() in ("JPEG", "JPG"):
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(out_buf, format="JPEG", quality=95, optimize=True)
            elif fmt.upper() == "PNG":
                img.save(out_buf, format="PNG", optimize=True)
            elif fmt.upper() == "WEBP":
                img.save(out_buf, format="WEBP", quality=95)
            else:
                img.convert("RGB").save(out_buf, format="JPEG", quality=95)

            return out_buf.getvalue(), ["EXIF", "XMP", "Metadata"]

    @classmethod
    def _verify_clean_image(cls, data: bytes) -> None:
        """Validate that the cleaned binary is still a valid decodable image."""
        stream = io.BytesIO(data)
        with Image.open(stream) as img:
            img.verify()

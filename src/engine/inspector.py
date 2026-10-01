"""Metadata inspector for detecting AI signatures and tags in image files."""
from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path
from typing import BinaryIO

from src.engine.models import ImageFormat, InspectionResult


class MetadataInspector:
    """Inspects raw image binaries to identify embedded metadata and AI provenance tags."""

    @classmethod
    def detect_format(cls, data: bytes) -> ImageFormat:
        if len(data) >= 3 and data[:3] == b"\xFF\xD8\xFF":
            return ImageFormat.JPEG
        if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
            return ImageFormat.PNG
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return ImageFormat.WEBP
        return ImageFormat.UNKNOWN

    @classmethod
    def inspect_file(cls, file_path: str | Path) -> InspectionResult:
        path = Path(file_path)
        data = path.read_bytes()
        return cls.inspect_bytes(data)

    @classmethod
    def inspect_bytes(cls, data: bytes) -> InspectionResult:
        fmt = cls.detect_format(data)
        result = InspectionResult(format=fmt, size_bytes=len(data))

        if fmt == ImageFormat.PNG:
            cls._inspect_png(data, result)
        elif fmt == ImageFormat.JPEG:
            cls._inspect_jpeg(data, result)
        elif fmt == ImageFormat.WEBP:
            cls._inspect_webp(data, result)
        else:
            cls._inspect_generic(data, result)

        return result

    @classmethod
    def _inspect_png(cls, data: bytes, result: InspectionResult) -> None:
        """Parse PNG chunks to detect metadata."""
        if len(data) < 8:
            return

        offset = 8
        data_len = len(data)

        while offset + 8 <= data_len:
            length = struct.unpack(">I", data[offset:offset + 4])[0]
            chunk_type = data[offset + 4:offset + 8]
            chunk_payload = data[offset + 8:offset + 8 + length]
            offset += 12 + length

            if chunk_type == b"eXIf":
                result.has_exif = True
                if "EXIF" not in result.detected_tags:
                    result.detected_tags.append("EXIF")

            elif chunk_type == b"iCCP":
                result.has_icc = True
                if "ICC" not in result.detected_tags:
                    result.detected_tags.append("ICC")

            elif chunk_type in (b"c2pa", b"caIp"):
                result.has_c2pa = True
                if "C2PA" not in result.detected_tags:
                    result.detected_tags.append("C2PA")
                result.ai_signatures.append("C2PA Content Credentials")

            elif chunk_type == b"tEXt":
                cls._parse_png_text(chunk_payload, result, compressed=False)

            elif chunk_type == b"zTXt":
                cls._parse_png_text(chunk_payload, result, compressed=True)

            elif chunk_type == b"iTXt":
                cls._parse_png_itxt(chunk_payload, result)

            elif chunk_type == b"XML:com.adobe.xmp":
                result.has_xmp = True
                if "XMP" not in result.detected_tags:
                    result.detected_tags.append("XMP")

    @classmethod
    def _parse_png_text(cls, payload: bytes, result: InspectionResult, compressed: bool) -> None:
        try:
            null_idx = payload.find(b"\x00")
            if null_idx == -1:
                return
            keyword = payload[:null_idx].decode("latin-1", errors="ignore")
            if compressed:
                compressed_text = payload[null_idx + 2:]
                text = zlib.decompress(compressed_text).decode("utf-8", errors="ignore")
            else:
                text = payload[null_idx + 1:].decode("latin-1", errors="ignore")

            cls._analyze_text_metadata(keyword, text, result)
        except Exception:
            pass

    @classmethod
    def _parse_png_itxt(cls, payload: bytes, result: InspectionResult) -> None:
        try:
            null_idx = payload.find(b"\x00")
            if null_idx == -1 or len(payload) < null_idx + 5:
                return
            keyword = payload[:null_idx].decode("utf-8", errors="ignore")
            comp_flag = payload[null_idx + 1]
            rest = payload[null_idx + 3:]
            idx2 = rest.find(b"\x00")
            if idx2 != -1:
                rest2 = rest[idx2 + 1:]
                idx3 = rest2.find(b"\x00")
                if idx3 != -1:
                    raw_val = rest2[idx3 + 1:]
                    if comp_flag == 1:
                        text = zlib.decompress(raw_val).decode("utf-8", errors="ignore")
                    else:
                        text = raw_val.decode("utf-8", errors="ignore")
                    cls._analyze_text_metadata(keyword, text, result)
        except Exception:
            pass

    @classmethod
    def _analyze_text_metadata(cls, keyword: str, text: str, result: InspectionResult) -> None:
        kw_lower = keyword.lower()
        if kw_lower in ("prompt", "workflow"):
            if "nodes" in text or "class_type" in text:
                result.has_comfyui_workflow = True
                if "ComfyUI Workflow" not in result.detected_tags:
                    result.detected_tags.append("ComfyUI Workflow")
                result.ai_signatures.append("ComfyUI Node Graph")
            else:
                result.has_sd_parameters = True
                if "Prompt Parameters" not in result.detected_tags:
                    result.detected_tags.append("Prompt Parameters")

        if kw_lower == "parameters":
            result.has_sd_parameters = True
            if "SD Parameters" not in result.detected_tags:
                result.detected_tags.append("SD Parameters")
            result.ai_signatures.append("Stable Diffusion Generation Parameters")

        if "c2pa" in text.lower() or "contentcredentials" in text.lower():
            result.has_c2pa = True
            if "C2PA" not in result.detected_tags:
                result.detected_tags.append("C2PA")

        if kw_lower in ("software", "comment", "description"):
            if any(k in text.lower() for k in ("midjourney", "novelai", "dall-e", "stablediffusion", "flux")):
                result.has_midjourney_meta = True
                if "AI Generator Tag" not in result.detected_tags:
                    result.detected_tags.append("AI Generator Tag")

    @classmethod
    def _inspect_jpeg(cls, data: bytes, result: InspectionResult) -> None:
        """Parse JPEG APP markers to detect metadata."""
        stream = io.BytesIO(data)
        if stream.read(2) != b"\xFF\xD8":
            return

        while True:
            marker = stream.read(2)
            if not marker or len(marker) < 2:
                break
            if marker[0] != 0xFF:
                break

            m_type = marker[1]
            if m_type in (0xD8, 0xD9):
                continue
            if 0xD0 <= m_type <= 0xD7 or m_type == 0x01:
                continue
            if m_type == 0xDA:
                break

            len_bytes = stream.read(2)
            if len(len_bytes) < 2:
                break
            length = struct.unpack(">H", len_bytes)[0]
            payload = stream.read(length - 2)

            if m_type == 0xE1:
                if payload.startswith(b"Exif\x00\x00"):
                    result.has_exif = True
                    if "EXIF" not in result.detected_tags:
                        result.detected_tags.append("EXIF")
                    cls._check_ai_in_exif(payload, result)
                elif payload.startswith(b"http://ns.adobe.com/xap/1.0/\x00"):
                    result.has_xmp = True
                    if "XMP" not in result.detected_tags:
                        result.detected_tags.append("XMP")
                    cls._check_ai_in_xmp(payload, result)

            elif m_type == 0xE2:
                if payload.startswith(b"ICC_PROFILE\x00"):
                    result.has_icc = True
                    if "ICC" not in result.detected_tags:
                        result.detected_tags.append("ICC")

            elif m_type == 0xEB:
                result.has_c2pa = True
                if "C2PA" not in result.detected_tags:
                    result.detected_tags.append("C2PA")
                result.ai_signatures.append("C2PA Content Credentials Manifest")

            elif m_type == 0xED:
                result.has_iptc = True
                if "IPTC" not in result.detected_tags:
                    result.detected_tags.append("IPTC")
                if b"trainedAlgorithmicMedia" in payload:
                    result.ai_signatures.append("IPTC DigitalSourceType (AI Generated)")

    @classmethod
    def _check_ai_in_exif(cls, payload: bytes, result: InspectionResult) -> None:
        text = payload.decode("latin-1", errors="ignore").lower()
        if any(w in text for w in ("midjourney", "dall-e", "stablediffusion", "novelai", "flux", "fooocus")):
            result.has_midjourney_meta = True
            result.ai_signatures.append("AI Generator in EXIF")

    @classmethod
    def _check_ai_in_xmp(cls, payload: bytes, result: InspectionResult) -> None:
        text = payload.decode("utf-8", errors="ignore").lower()
        if "c2pa" in text or "contentcredentials" in text:
            result.has_c2pa = True
            if "C2PA" not in result.detected_tags:
                result.detected_tags.append("C2PA")
        if any(w in text for w in ("midjourney", "dall-e", "stablediffusion", "prompt", "parameters")):
            result.ai_signatures.append("AI Prompt/Provenance in XMP")

    @classmethod
    def _inspect_webp(cls, data: bytes, result: InspectionResult) -> None:
        """Parse WebP RIFF container chunks."""
        if len(data) < 12:
            return

        offset = 12
        total_len = len(data)

        while offset + 8 <= total_len:
            fourcc = data[offset:offset + 4]
            chunk_size = struct.unpack("<I", data[offset + 4:offset + 8])[0]
            chunk_payload = data[offset + 8:offset + 8 + chunk_size]
            offset += 8 + chunk_size + (chunk_size % 2)

            if fourcc == b"EXIF":
                result.has_exif = True
                if "EXIF" not in result.detected_tags:
                    result.detected_tags.append("EXIF")
                cls._check_ai_in_exif(chunk_payload, result)

            elif fourcc == b"XMP ":
                result.has_xmp = True
                if "XMP" not in result.detected_tags:
                    result.detected_tags.append("XMP")
                cls._check_ai_in_xmp(chunk_payload, result)

            elif fourcc == b"ICCP":
                result.has_icc = True
                if "ICC" not in result.detected_tags:
                    result.detected_tags.append("ICC")

    @classmethod
    def _inspect_generic(cls, data: bytes, result: InspectionResult) -> None:
        """Heuristic scan across raw bytes."""
        text = data[:4096].decode("latin-1", errors="ignore").lower()
        if "exif" in text:
            result.has_exif = True
            result.detected_tags.append("EXIF")
        if "xmp" in text or "http://ns.adobe.com" in text:
            result.has_xmp = True
            result.detected_tags.append("XMP")

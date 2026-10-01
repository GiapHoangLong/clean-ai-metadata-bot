"""Unit tests for Telegram response formatter."""
from pathlib import Path
from src.bot.formatter import format_clean_report, format_quota_message, format_start_message
from src.engine.models import ImageFormat, StripResult


def test_format_clean_report_for_photo() -> None:
    res = StripResult(
        format=ImageFormat.JPEG,
        input_path=Path("in.jpg"),
        output_path=Path("out.jpg"),
        size_before=104243,
        size_after=131686,
        dropped_tags=["ICC"],
        is_lossless=True,
        success=True,
    )

    caption = format_clean_report(
        result=res,
        used_quota=1,
        daily_limit=50,
        is_photo=True,
        display_filename="clean_01.jpg",
    )

    assert "clean_01.jpg" in caption
    assert "128.6 KB" in caption
    assert "🧹 Đã làm sạch 1/1 ảnh" in caption
    assert "101.8 KB → 128.6 KB" in caption
    assert "📦 Đã bỏ: ICC" in caption
    assert "🆓 Free: đã dùng 1/50 lượt hôm nay · còn 49" in caption
    assert "Lưu ý: Bot đã gỡ sạch thông tin ngầm" in caption
    assert "Mẹo: Ảnh này đã bị Telegram tự động nén" in caption


def test_format_clean_report_for_document() -> None:
    res = StripResult(
        format=ImageFormat.PNG,
        input_path=Path("test_art.png"),
        output_path=Path("clean_test_art.png"),
        size_before=524288,
        size_after=419430,
        dropped_tags=["ComfyUI Workflow", "SD Parameters", "EXIF"],
        is_lossless=True,
        success=True,
    )

    caption = format_clean_report(
        result=res,
        used_quota=10,
        daily_limit=50,
        is_photo=False,
        display_filename="clean_test_art.png",
    )

    assert "clean_test_art.png" in caption
    assert "📦 Đã bỏ: ComfyUI Workflow, SD Parameters, EXIF" in caption
    assert "🆓 Free: đã dùng 10/50 lượt hôm nay · còn 40" in caption
    assert "ảnh gửi dạng Photo" not in caption

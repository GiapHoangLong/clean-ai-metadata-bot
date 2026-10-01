"""Message formatting utility for CleanAI Telegram Bot."""
from __future__ import annotations

from src.engine.models import StripResult


def format_clean_report(
    result: StripResult,
    used_quota: int,
    daily_limit: int,
    is_photo: bool,
    display_filename: str,
    is_video: bool = False,
) -> str:
    """
    Format user-facing response message matching the exact Telegram Bot specification.
    Supports both Image and Video media reports.
    """
    remaining = max(0, daily_limit - used_quota)
    size_after_kb = result.size_after_kb
    size_before_kb = result.size_before_kb

    # Dropped tags string
    if result.dropped_tags:
        dropped_str = ", ".join(result.dropped_tags)
    else:
        dropped_str = "Không phát hiện metadata thừa"

    media_type_label = "video" if is_video else "ảnh"

    lines = [
        f"{display_filename}",
        f"{size_after_kb:.1f} KB",
        "",
        f"🧹 Đã làm sạch 1/1 {media_type_label}",
        f"📦 {size_before_kb:.1f} KB → {size_after_kb:.1f} KB",
        f"📦 Đã bỏ: {dropped_str}",
        f"🆓 Free: đã dùng {used_quota}/{daily_limit} lượt hôm nay · còn {remaining}",
        "ℹ️ Lưu ý: Bot đã gỡ sạch thông tin ngầm (prompt, thẻ AI). Tuy nhiên một số mạng xã hội vẫn có thể tự quét hình ảnh/video để nhận diện.",
    ]

    if is_photo:
        lines.append('💡 Mẹo: Ảnh này đã bị Telegram tự động nén. Hãy chọn "Gửi dưới dạng tệp" (Send as File) để giữ nguyên độ nét gốc nhé!')
    elif is_video:
        lines.append('💡 Mẹo: Nếu gửi dạng Video thường, Telegram có thể tự nén lại. Hãy chọn "Gửi dưới dạng tệp" (Send as File) để giữ chất lượng gốc!')

    return "\n".join(lines)


def format_start_message(daily_limit: int) -> str:
    """Format the welcome /start message."""
    return (
        "👋 Chào bạn! Tôi là **CleanAI Metadata Bot**.\n\n"
        "🧹 **Chức năng chính:**\n"
        "• Xóa sạch 100% metadata do AI tạo ra (Midjourney, Stable Diffusion, ComfyUI, DALL-E, Sora, Runway, Kling...)\n"
        "• Hỗ trợ cả **Hình Ảnh** (JPG, PNG, WebP) và **Video** (MP4, MOV, WebM, MKV)\n"
        "• Bóc tách EXIF, XMP, IPTC, C2PA Content Credentials, Prompt parameters, ComfyUI workflow JSON\n"
        "• **100% Lossless:** Giữ nguyên vẹn chất lượng điểm ảnh và khung hình video gốc\n\n"
        f"🆓 **Hạn mức miễn phí:** {daily_limit} lượt/ngày (tự động reset 00:00 hàng ngày)\n\n"
        "💡 **Cách sử dụng:**\n"
        "• Gửi ảnh hoặc video cho bot (Khuyên dùng: **Send as File / Gửi dưới dạng tệp** để giữ nguyên chất lượng gốc)\n"
        "• Gõ `/quota` để kiểm tra số lượt còn lại hôm nay\n"
        "• Gõ `/help` để xem thêm thông tin chi tiết."
    )


def format_quota_message(used: int, daily_limit: int) -> str:
    """Format /quota command reply."""
    remaining = max(0, daily_limit - used)
    return (
        "📊 **Thông tin hạn mức hôm nay:**\n\n"
        f"• Đã dùng: **{used}/{daily_limit}** lượt\n"
        f"• Còn lại: **{remaining}** lượt\n"
        "• Tự động làm mới vào: **00:00 (GMT+7)** hàng ngày."
    )

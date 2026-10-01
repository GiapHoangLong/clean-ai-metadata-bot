"""Telegram update handlers for commands and media messages (Images & Videos)."""
from __future__ import annotations

import logging
from pathlib import Path
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.bot.formatter import format_clean_report, format_quota_message, format_start_message
from src.config import DAILY_FREE_LIMIT, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB
from src.db.quota_manager import QuotaManager
from src.engine.binary_stripper import BinaryStripper
from src.engine.video_stripper import VideoStripper
from src.utils.file_cleanup import temporary_processing_directory

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not update.effective_message:
        return
    text = format_start_message(DAILY_FREE_LIMIT)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.effective_message:
        return
    help_text = (
        "📖 **Hướng dẫn chi tiết:**\n\n"
        "1️⃣ **Định dạng được hỗ trợ:**\n"
        "• **Hình ảnh:** JPG, JPEG, PNG, WebP\n"
        "• **Video:** MP4, MOV, WebM, MKV (Dung lượng tối đa 20MB theo quy định Telegram)\n\n"
        "2️⃣ **Tại sao nên gửi dạng File (Send as File)?**\n"
        "• Khi gửi dạng thường (Photo/Video), ứng dụng Telegram sẽ tự động nén làm giảm độ nét.\n"
        "• Khi gửi dạng **File/Document**, Telegram giữ nguyên vẹn 100% dữ liệu gốc.\n\n"
        "3️⃣ **Dấu vết nào được làm sạch?**\n"
        "• EXIF, XMP, IPTC, C2PA Content Credentials\n"
        "• ComfyUI Node Graph JSON, Stable Diffusion prompts & seed parameters\n"
        "• Video QuickTime container metadata, AI generation atoms (Sora, Runway, Kling...)\n\n"
        f"4️⃣ **Hạn mức sử dụng:** {DAILY_FREE_LIMIT} lượt/ngày miễn phí cho mỗi người dùng."
    )
    await update.effective_message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def quota_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /quota command."""
    if not update.effective_user or not update.effective_message:
        return
    user_id = update.effective_user.id
    used, remaining = await QuotaManager.get_user_quota(user_id)
    text = format_quota_message(used, DAILY_FREE_LIMIT)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def process_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo, video, and document media submissions."""
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    user_id = user.id
    is_photo = bool(message.photo)
    is_video = bool(message.video)
    is_document = bool(message.document)

    if not is_photo and not is_video and not is_document:
        await message.reply_text(
            "❌ Định dạng không được hỗ trợ. Vui lòng gửi file ảnh (JPG, PNG, WebP) hoặc video (MP4, MOV, WebM)."
        )
        return

    # Check and consume quota atomically
    allowed, used_count, remaining = await QuotaManager.check_and_consume_quota(user_id)
    if not allowed:
        await message.reply_text(
            f"⚠️ **Hết hạn mức hôm nay:**\n"
            f"Bạn đã sử dụng hết {DAILY_FREE_LIMIT}/{DAILY_FREE_LIMIT} lượt miễn phí của ngày hôm nay.\n"
            f"Hạn mức sẽ tự động đặt lại vào 00:00 (GMT+7) ngày mai!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    status_msg = await message.reply_text("⏳ Đang tải và làm sạch siêu dữ liệu AI...")

    async with temporary_processing_directory(session_id=f"user_{user_id}_{message.message_id}") as work_dir:
        try:
            is_media_video = False

            # Case 1: Photo
            if is_photo:
                photo_obj = message.photo[-1]
                if photo_obj.file_size and photo_obj.file_size > MAX_FILE_SIZE_BYTES:
                    await status_msg.edit_text(f"❌ Dung lượng ảnh vượt quá giới hạn ({MAX_FILE_SIZE_MB}MB).")
                    return
                tg_file = await photo_obj.get_file()
                input_file_path = work_dir / "input_photo.jpg"
                await tg_file.download_to_drive(custom_path=input_file_path)
                display_filename = "clean_01.jpg"
                output_ext = ".jpg"

            # Case 2: Video
            elif is_video:
                video_obj = message.video
                is_media_video = True
                if video_obj.file_size and video_obj.file_size > MAX_FILE_SIZE_BYTES:
                    await status_msg.edit_text(
                        f"❌ Dung lượng video ({video_obj.file_size / (1024*1024):.1f}MB) vượt quá giới hạn ({MAX_FILE_SIZE_MB}MB) cho phép của Telegram Bot API."
                    )
                    return
                tg_file = await video_obj.get_file()
                orig_name = video_obj.file_name or "video.mp4"
                ext = Path(orig_name).suffix.lower() or ".mp4"
                input_file_path = work_dir / f"input_video{ext}"
                await tg_file.download_to_drive(custom_path=input_file_path)
                clean_stem = Path(orig_name).stem
                display_filename = f"clean_{clean_stem}{ext}" if not clean_stem.startswith("clean_") else f"{clean_stem}{ext}"
                output_ext = ext

            # Case 3: Document (sent as file)
            else:
                doc = message.document
                if not doc:
                    return
                if doc.file_size and doc.file_size > MAX_FILE_SIZE_BYTES:
                    await status_msg.edit_text(f"❌ Dung lượng tệp vượt quá giới hạn ({MAX_FILE_SIZE_MB}MB).")
                    return

                orig_name = doc.file_name or "file.bin"
                orig_path = Path(orig_name)
                ext = orig_path.suffix.lower() if orig_path.suffix else ""
                
                # Check extension
                image_exts = {".jpg", ".jpeg", ".png", ".webp"}
                video_exts = {".mp4", ".mov", ".webm", ".mkv", ".avi"}

                if ext in video_exts:
                    is_media_video = True
                elif ext not in image_exts:
                    await status_msg.edit_text(
                        "❌ Định dạng không được hỗ trợ. Vui lòng gửi ảnh (JPG, PNG, WebP) hoặc video (MP4, MOV, WebM)."
                    )
                    return

                tg_file = await doc.get_file()
                input_file_path = work_dir / f"input_doc{ext}"
                await tg_file.download_to_drive(custom_path=input_file_path)

                clean_stem = orig_path.stem
                if not clean_stem.startswith("clean_"):
                    display_filename = f"clean_{clean_stem}{ext}"
                else:
                    display_filename = f"{clean_stem}{ext}"
                output_ext = ext

            output_file_path = work_dir / f"output_clean{output_ext}"

            # Execute stripping
            if is_media_video:
                result = VideoStripper.strip_video(input_file_path, output_file_path)
            else:
                result = BinaryStripper.strip_file(input_file_path, output_file_path)

            if not result.success or not output_file_path.exists():
                await status_msg.edit_text(f"❌ Xử lý thất bại: {result.error_message or 'Lỗi định dạng không xác định'}")
                return

            # Format response caption
            caption = format_clean_report(
                result=result,
                used_quota=used_count,
                daily_limit=DAILY_FREE_LIMIT,
                is_photo=is_photo,
                display_filename=display_filename,
                is_video=is_media_video,
            )

            # Reply with clean Document (guarantees zero recompression)
            await message.reply_document(
                document=output_file_path,
                filename=display_filename,
                caption=caption,
            )

            # Clean up status notification
            try:
                await status_msg.delete()
            except Exception:
                pass

        except Exception as e:
            logger.exception("Error processing media from user %s", user_id)
            await status_msg.edit_text(f"❌ Đã xảy ra lỗi trong quá trình xử lý: {e}")

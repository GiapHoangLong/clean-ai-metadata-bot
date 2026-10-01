# BRIEF HANDOFF: CLEAN AI METADATA TELEGRAM BOT (WAVE 1)
**Ngày:** 01/10/2026 | **Phiên:** Wave 1 | **Chuẩn:** `/bto-agent-team` & BTO

## 1. Đọc trước (Tối đa 3 tài liệu)
1. Kế hoạch & Đặc tả: `plan_clean_ai_metadata_telegram_bot.md`
2. Kiến trúc Data Flow & Component Diagram (trong file Plan)
3. Ticket Specification Standard (Mục 4 Global Rules)

## 2. Trạng thái xuất phát
- Repo `d:/Clean Metadata` vừa khởi tạo, chưa có code.
- Môi trường: Python 3.11.5, `uv 0.11.26`, OS Windows 11.
- Không có dependency ngoài chưa được phê duyệt.

## 3. Setup & Roles
- **Worktree / Module Lock:**
  - Role Data/Engine: `src/engine/*`, `tests/test_engine.py`, `tests/samples/*`
  - Role Backend: `src/bot/*`, `src/config.py`, `src/db/*`, `main.py`, `.env.example`
  - Role Coordinator / Reviewer: `tests/test_e2e.py`, `guard_check.py`, `README.md`
- **Tên scratchpad:** Độc lập per role.

## 4. Contract per Ticket
| Ticket | Role | File được phép chạm | Bằng chứng chấp nhận (Acceptance Evidence) |
|---|---|---|---|
| **TEC-AI-1: Core Binary Stripper Engine** | Data/Engine | `src/engine/*`, `tests/test_engine.py` | Unit test pass 100%, 0 tag EXIF/XMP/C2PA/ComfyUI còn lại sau khi strip, hash pixel giữ nguyên. |
| **TEC-AI-2: Quota & Storage Engine** | Backend | `src/db/*`, `src/config.py` | Kiểm tra giới hạn 3 lượt/ngày, auto-reset sau 24h, test pass. |
| **TEC-AI-3: Telegram Bot Media Handlers** | Backend | `src/bot/*`, `main.py`, `.env.example` | Nhận photo/doc, trả doc clean_<name> kèm caption đúng template. |
| **TEC-AI-4: Test Suite & Guard Verification** | Coordinator | `tests/test_e2e.py`, `guard_check.py` | Guard script chạy local verify toàn bộ pipeline xanh không lỗi. |

## 5. Luật bất biến
- Không làm giảm chất lượng ảnh gốc (Lossless binary strip).
- Không hardcode secret (Token bot qua `.env` + `.gitignore`).
- Dọn dẹp file tạm ngay sau khi gửi kết quả về cho user.

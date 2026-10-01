---
status: planned
intent: intent/2026-10-01-production-deployment.md
date: 2026-10-01
---

# Plan: Triển Khai Production & Thiết Lập Phòng Tuyến Bảo Mật BTO Secrets

## 1. Files Cần Tạo / Chạm (Files)
1. `Dockerfile`: Image nền Debian/Python 3.11-slim, cài đặt ffmpeg, uv, non-root user, entry point.
2. `docker-compose.yml`: Khai báo service, volume mapping cho `data/` và `scratch/`, nạp biến môi trường.
3. `deploy/cleanai-bot.service`: File cấu hình systemd cho ai thích chạy trực tiếp trên Linux không qua Docker.
4. `scripts/scan_secrets.py`: Script tự động rà quét toàn bộ staged files / git diff để chặn đẩy API key lên GitHub.
5. `docs/DEPLOYMENT.md`: Sổ tay hướng dẫn vận hành từng bước (Runbook) cho người quản trị.

## 2. Rủi Ro Tiềm Ẩn & Cách Bắt Lỗi (Risks & Mitigations)
| Rủi Ro | Hậu Quả | Cách Kiểm Soát & Ngăn Chặn |
|---|---|---|
| Lộ Token khi push Git | Kẻ xấu cướp quyền bot, spam người dùng | Chạy `scan_secrets.py` chặn commit; `.env` đã có trong `.gitignore`. Hướng dẫn xoay token. |
| Mất dữ liệu Quota khi reboot | User bị reset lượt dùng bất thường | Mount Volume `data/` ra ngoài thư mục host trong Docker. |
| Tràn RAM khi xử lý nhiều file | Bot bị OOM kill | Thư mục tạm `scratch/` được dọn sạch sau mỗi request; giới hạn file size 20MB. |
| Thiếu ffmpeg trên môi trường prod | Bot xử lý ảnh được nhưng video báo lỗi | Tích hợp sẵn `ffmpeg` trong image Dockerfile. |

## 3. Bằng Chứng Nghiệm Thu (Proof)
- Chạy `python scripts/scan_secrets.py` -> Pass xanh (0 secret bị commit).
- Kiểm tra file Dockerfile và docker-compose.yml hợp lệ về mặt cấu trúc.
- Quy trình xoay token (Rotate Key) được hướng dẫn chi tiết.

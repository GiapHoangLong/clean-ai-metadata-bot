---
status: approved
date: 2026-10-01
author: Technical Lead (BTO)
---

# Intent: Đưa CleanAI Metadata Stripper Bot Lên Production & Bảo Mật Key Tuyệt Đối

## Problem
Bot hiện đang chạy dưới dạng tiến trình local trên máy tính cá nhân. Khi tắt máy hoặc ngắt mạng, Bot sẽ ngừng hoạt động. Đồng thời, bot token cần được bảo mật theo tiêu chuẩn BTO Secrets để tránh rò rỉ khi đẩy mã nguồn lên GitHub hoặc khi deploy lên cloud server.

## Outcome
1. **Production Deployment Containerized:** Có thể triển khai trên bất kỳ máy chủ Linux VPS (DigitalOcean, Hetzner, AWS EC2) hoặc nền tảng PaaS (Railway, Fly.io, Render) chỉ với 1 lệnh (`docker compose up -d` hoặc `systemd`).
2. **Dữ Liệu Bền Vững (Data Persistence):** CSDL SQLite (`data/bot.db`) được mount volume an toàn, không bị mất lịch sử đếm quota khi restart container.
3. **Bảo Mật Key Tuyệt Đối (`/bto-secrets`):**
   - 0 byte secret lọt vào Git history (đã verify).
   - Cơ chế nạp biến môi trường an toàn trên host/server.
   - Quy trình xoay key (Rotate token) và script quét tự động trước khi push.
4. **Tự Động Phục Hồi (Auto-Restart):** Khi tiến trình gặp sự cố bất ngờ hoặc server reboot, bot tự động khởi chạy lại ngay lập tức (`restart: unless-stopped`).

## Constraints
- Không phụ thuộc vào các dịch vụ cloud tốn kém (chạy tốt trên VPS $4-5/tháng hoặc gói Free PaaS).
- Phải có sẵn `ffmpeg` trong container để xử lý video lossless.
- Tuân thủ nguyên tắc non-root container (chạy bằng user `appuser` để bảo mật máy chủ).

## Out of Scope
- Chưa xây dựng cụm cluster multi-instance (vì Telegram Long-Polling yêu cầu single active poller per token; scaling webhook sẽ làm ở giai đoạn sau nếu tải > 10,000 req/ngày).

## Open Questions
- Không có. Sẵn sàng đóng gói và triển khai.

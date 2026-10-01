# Hướng Dẫn Triển Khai Production & Bảo Mật Key
**Dự án:** CleanAI Metadata Stripper - Telegram Bot  
**Chuẩn:** `/bto-sdlc` & `/bto-secrets`

---

## 1. Bảo Mật Key Theo Chuẩn `/bto-secrets`

### 1.1. Cảnh báo xoay Token (Rotate Key)
Khi thử nghiệm ở máy cá nhân hoặc trao đổi trong chat, chuỗi token có thể đã lưu lại trên màn hình hoặc lịch sử.  
**Trước khi đưa lên Production chính thức, hãy luôn xoay token mới:**
1. Mở Telegram, nhắn `@BotFather`
2. Gõ `/mybots` $\rightarrow$ Chọn bot của bạn $\rightarrow$ Chọn **API Token**
3. Bấm **Revoke current token** để hủy token cũ và nhận token mới tinh.
4. Điền token mới vào môi trường máy chủ Production.

### 1.2. Ba tầng bảo mật Secret trên Production
1. **Tuyệt đối không commit file `.env` lên GitHub:**
   - File `.env` đã được đưa vào `.gitignore`.
   - Trước khi push, luôn chạy:
     ```bash
     uv run python scripts/scan_secrets.py
     ```
2. **Trên Máy Chủ VPS (Linux):**
   - Đặt quyền truy cập file nghiêm ngặt:
     ```bash
     chmod 600 .env
     ```
   - Chỉ duy nhất user chạy tiến trình mới có quyền đọc file này.
3. **Trên Nền Tảng Cloud / PaaS (Railway, Fly.io, Render):**
   - Không upload file `.env`.
   - Điền trực tiếp biến `TELEGRAM_BOT_TOKEN` vào mục **Variables / Secrets** trên giao diện web của họ.

---

## 2. Triển Khai Bằng Docker Compose (Khuyên Dùng Nhất)

### Bước 1: Chuẩn bị máy chủ VPS (Ubuntu/Debian)
Cài đặt Docker và Docker Compose trên VPS:
```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

### Bước 2: Đẩy mã nguồn lên VPS
Clone repo về thư mục trên VPS:
```bash
git clone <URL_REPO_GITHUB_CUA_BAN> /opt/cleanai-bot
cd /opt/cleanai-bot
```

### Bước 3: Tạo file cấu hình môi trường
```bash
cp .env.example .env
nano .env
```
*(Điền `TELEGRAM_BOT_TOKEN` mới và lưu lại)*.

### Bước 4: Khởi động Bot chạy ngầm vĩnh viễn
```bash
docker compose up -d --build
```

### Bước 5: Kiểm tra trạng thái & Nhật ký log
```bash
# Xem logs bot
docker compose logs -f

# Xem trạng thái container
docker compose ps
```
Bot sẽ tự động chạy ngầm, tự bật lại khi server reboot (`restart: unless-stopped`) và dữ liệu SQLite được lưu an toàn tại thư mục `./data` trên VPS.

---

## 3. Triển Khai Miễn Phí Trên PaaS (Railway / Render)

Nếu bạn không muốn quản lý máy chủ VPS:

1. **Đẩy mã nguồn lên GitHub Repo.**
2. **Dịch vụ đang hoạt động trực tiếp trên [Render.com](https://render.com):**
   - **Service Name:** `clean-ai-metadata-bot`
   - **Dashboard:** [https://dashboard.render.com/web/srv-dauts0fpn0mc7395rmmg](https://dashboard.render.com/web/srv-dauts0fpn0mc7395rmmg)
   - **Public URL:** [https://clean-ai-metadata-bot.onrender.com](https://clean-ai-metadata-bot.onrender.com) (HTTP 200 OK - Health Check)
   - **Region:** Singapore
   - **Plan:** Free ($0/tháng)
   - **Environment Variables:** `TELEGRAM_BOT_TOKEN`, `DAILY_FREE_LIMIT=50`
   - **Auto-Deploy:** Tự động kích hoạt build & deploy khi có commit mới trên nhánh `main`.

---

## 4. Cập Nhật Khi Có Bản Code Mới (Zero Downtime)

Mỗi khi bạn commit tính năng mới vào Git:
```bash
# Trên máy chủ VPS:
cd /opt/cleanai-bot
git pull origin main
docker compose up -d --build
```
Container mới sẽ được build và hoán đổi trong chưa đầy 3 giây mà không làm gián đoạn người dùng.

# CleanAI Metadata Stripper - Telegram Bot

Hệ thống Bot Telegram chuyên biệt để phát hiện và làm sạch **100% siêu dữ liệu (metadata)** do các công cụ Generative AI tạo ra (Midjourney, Stable Diffusion, ComfyUI, DALL-E 3, Adobe Firefly, Flux, NovelAI...).  
Được phát triển theo tiêu chuẩn **Build to Own (BTO)** và playbook **`/bto-agent-team` Wave 1**.

---

## 1. Tính Năng Nổi Bật (Key Features)

- **100% Lossless Binary Stripping:**
  - Không decode và re-encode lại pixel stream, giữ nguyên 100% độ sắc nét và màu sắc gốc.
  - Tốc độ xử lý siêu nhanh (< 5ms cho ảnh 4K).
- **Làm sạch triệt để mọi dấu vết AI:**
  - **PNG:** Chunks `tEXt`, `zTXt`, `iTXt` (Stable Diffusion prompt, seed, sampler, CFG; ComfyUI node graph JSON), `c2pa`, `caIp`, `eXIf`, `iCCP`.
  - **JPEG:** Phân vùng marker `APP1` (Exif, XMP), `APP2` (ICC Profile), `APP11` (C2PA/JUMBF Content Credentials của OpenAI, Adobe, Microsoft), `APP13` (IPTC `trainedAlgorithmicMedia`).
  - **WebP:** Chunks `EXIF`, `XMP `, `ICCP`.
  - **Video:** Hỗ trợ MP4, MOV, WebM qua direct stream copy (ffmpeg).
- **Tương tác Telegram thân thiện & Minh bạch:**
  - Tiếp nhận cả ảnh thường (**Photo**) và tệp gốc (**Document**).
  - Trả về tệp dạng **Document** (`clean_<filename>`) để ngăn Telegram tự động nén.
  - Hiển thị đầy đủ thông số: dung lượng trước -> sau, danh sách tag đã bỏ, quota còn lại trong ngày.
- **Hạn mức Miễn phí (Free Quota):**
  - Mặc định **50 lượt/ngày/user** (quản lý bởi SQLite async atomic transactions).
  - Tự động làm mới lúc **00:00 (GMT+7)** hàng ngày.

---

## 2. Triển khai Production 1-Click
Xem chi tiết tại [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) hoặc sử dụng Dockerfile đi kèm.

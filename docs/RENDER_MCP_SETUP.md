# Hướng Dẫn Cấu Hình Render MCP Server (Model Context Protocol)

Tài liệu hướng dẫn kết nối **Render MCP Server** vào AI IDE (Antigravity IDE, Cursor, Claude Desktop/Code) để quản lý, deploy và giám sát bot Telegram trực tiếp bằng câu lệnh ngôn ngữ tự nhiên.

---

## 1. Sơ Đồ Kiến Trúc Hoạt Động (Mermaid Architecture)

```mermaid
flowchart TD
    subgraph Client["AI Client (Antigravity IDE / Cursor / Claude)"]
        User["Người dùng / Dev"] -->|"Chat: 'Deploy lại bot & xem log'"| AIAgent["AI Assistant / Agent"]
        AIAgent -->|"MCP Protocol (JSON-RPC)"| MCPRunner["mcp-remote / Stdio Process"]
    end

    subgraph RenderMCPCloud["Render Hosted MCP Gateway"]
        MCPRunner -->|"HTTPS Bearer Token"| HostedMCP["https://mcp.render.com/mcp"]
    end

    subgraph RenderPlatform["Hạ Tầng Render.com Cloud"]
        HostedMCP -->|"Render REST API"| Services["Web Services (CleanAI Bot)"]
        HostedMCP --> Deploys["Deploy Engine"]
        HostedMCP --> Logs["Live Log Streams"]
        HostedMCP --> Metrics["CPU / RAM Metrics"]
    end
```

---

## 2. Bước 1: Tạo Render API Key

1. Đăng nhập vào Render Dashboard: [dashboard.render.com](https://dashboard.render.com).
2. Vào trang **Account Settings** $\rightarrow$ **API Keys** (hoặc truy cập trực tiếp: [dashboard.render.com/u/settings?add-api-key](https://dashboard.render.com/u/settings?add-api-key)).
3. Bấm **Create API Key**:
   * Name: `antigravity-render-mcp` (hoặc tên gợi nhớ bất kỳ).
4. **Copy API Key** vừa tạo (dạng `rnd_...`).

> [!WARNING]
> Render API Key có toàn quyền quản lý tài nguyên trên tài khoản của bạn. Tuyệt đối **không** commit key này vào git repo hoặc chia sẻ công khai.

---

## 3. Bước 2: Cấu Hình Vào Antigravity IDE

Dự án đã tạo sẵn file cấu hình MCP tại [`.agents/mcp_config.json`](file:///d:/Clean%20Metadata/.agents/mcp_config.json) (đã được thêm vào `.gitignore` để bảo vệ an toàn).

### Cách A: Dùng Biến Môi Trường Hệ Thống (Khuyến nghị - An toàn nhất)
Thiết lập `RENDER_API_KEY` vào biến môi trường Windows để mọi công cụ tự động nhận mà không cần lưu key trong bất kỳ file nào:

Mở PowerShell và chạy lệnh sau (thay `<Dán_Key_Của_Bạn>`):
```powershell
[Environment]::SetEnvironmentVariable("RENDER_API_KEY", "<Dán_Key_Của_Bạn>", "User")
```

File `.agents/mcp_config.json` sẽ tự động đọc biến `${RENDER_API_KEY}`:
```json
{
  "mcpServers": {
    "render": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.render.com/mcp",
        "--header",
        "Authorization: Bearer ${RENDER_API_KEY}"
      ],
      "env": {
        "RENDER_API_KEY": "${RENDER_API_KEY}"
      }
    }
  }
}
```

### Cách B: Điền trực tiếp vào `.agents/mcp_config.json`
Nếu không muốn đặt biến môi trường toàn cục, bạn mở file [`.agents/mcp_config.json`](file:///d:/Clean%20Metadata/.agents/mcp_config.json) và thay thế chuỗi `<YOUR_API_KEY>` bằng key `rnd_...`:
```json
{
  "mcpServers": {
    "render": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.render.com/mcp",
        "--header",
        "Authorization: Bearer rnd_xxxxxxxxxxxxxxxxxxxx"
      ],
      "env": {
        "RENDER_API_KEY": "rnd_xxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

---

## 4. Bước 3: Cấu Hình Cho Các AI App Khác (Nếu Dùng Song Song)

### Dành cho Cursor
Mở hoặc tạo file `~/.cursor/mcp.json` và thêm:
```json
{
  "mcpServers": {
    "render": {
      "url": "https://mcp.render.com/mcp",
      "headers": {
        "Authorization": "Bearer rnd_your_api_key_here"
      }
    }
  }
}
```

### Dành cho Claude Desktop
Mở `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "render": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.render.com/mcp",
        "--header",
        "Authorization: Bearer rnd_your_api_key_here"
      ],
      "env": {
        "RENDER_API_KEY": "rnd_your_api_key_here"
      }
    }
  }
}
```

### Dành cho Claude Code (CLI)
Chạy lệnh:
```bash
claude mcp add --transport http render https://mcp.render.com/mcp --header "Authorization: Bearer rnd_your_api_key_here"
```

---

## 5. Danh Sách Câu Lệnh Prompt Thực Chiến

Sau khi kết nối, bạn có thể ra lệnh trực tiếp cho AI trong chat:

1. **Quản lý Workspace:**
   * *"Liệt kê danh sách Workspace của tôi trên Render"* (`list_workspaces`)
   * *"Chọn workspace mặc định là TechArk"* (`set_workspace`)

2. **Quản lý Service & Deploy:**
   * *"Liệt kê tất cả các dịch vụ đang chạy trên Render"* (`list_services`)
   * *"Kiểm tra trạng thái deploy của service clean-ai-metadata-bot"* (`list_deploys` / `get_deploy`)
   * *"Trigger một bản build mới cho bot và xóa build cache"* (`trigger_deploy`)

3. **Giám sát & Logs:**
   * *"Lấy 30 dòng logs mới nhất của service clean-ai-metadata-bot"* (`list_logs`)
   * *"Xem mức tiêu thụ CPU và RAM của bot trong 24 giờ qua"* (`get_metrics`)

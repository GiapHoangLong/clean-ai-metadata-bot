"""BTO Secrets Pre-Push Scanner.
Scans git commits, staged files, and working tree for sensitive tokens and keys.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Safe UTF-8 reconfiguration on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Sensitive token patterns (BTO Standard)
PATTERNS = [
    (r"(?i)TELEGRAM_BOT_TOKEN\s*=\s*['\"]?[0-9]{8,11}:[a-zA-Z0-9_-]{30,}['\"]?", "Telegram Bot Token"),
    (r"[0-9]{8,11}:[a-zA-Z0-9_-]{35}", "Raw Telegram Token string"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key"),
    (r"ghp_[a-zA-Z0-9]{36,}", "GitHub Personal Access Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----", "Private Key Header"),
]


def check_git_tracked_files() -> list[str]:
    """Scan all files tracked by git to ensure no secrets have been committed."""
    findings = []
    try:
        tracked_files = subprocess.check_output(
            ["git", "ls-files"], text=True, errors="ignore"
        ).splitlines()

        for file_str in tracked_files:
            p = Path(file_str)
            if not p.is_file() or p.name in (".env.example",):
                continue

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for pattern, name in PATTERNS:
                    matches = re.findall(pattern, content)
                    if matches:
                        findings.append(f"❌ File đã tracked '{file_str}' chứa {name}!")
            except Exception:
                pass

    except Exception as e:
        findings.append(f"Lỗi kiểm tra git: {e}")

    return findings


def check_staged_diff() -> list[str]:
    """Scan staged changes (git diff --cached)."""
    findings = []
    try:
        diff_output = subprocess.check_output(
            ["git", "diff", "--cached"], text=True, errors="ignore"
        )
        if not diff_output:
            return []

        for line in diff_output.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                for pattern, name in PATTERNS:
                    if re.search(pattern, line):
                        if "YOUR_TELEGRAM_BOT_TOKEN_HERE" in line:
                            continue
                        findings.append(f"❌ Phát hiện {name} trong git staged diff: {line[:50]}...")
    except Exception as e:
        findings.append(f"Lỗi đọc diff: {e}")

    return findings


def main() -> int:
    print("=" * 65)
    print("🔒 BTO SECRETS SCANNER (Kiểm Tra Bảo Mật Trước Khi Push)")
    print("=" * 65)

    findings = check_git_tracked_files() + check_staged_diff()

    if findings:
        print("\n⚠️  CẢNH BÁO BẢO MẬT: PHÁT HIỆN SECRET TRONG REPO!")
        for f in findings:
            print(f"   {f}")
        print("\n👉 HÃY DỪNG LẠI! Xóa secret khỏi commit trước khi push lên GitHub!")
        print("=" * 65)
        return 1
    else:
        print("✅ AN TOÀN TUYỆT ĐỐI: Không phát hiện bất kỳ secret nào trong Git!")
        print("=" * 65)
        return 0


if __name__ == "__main__":
    sys.exit(main())

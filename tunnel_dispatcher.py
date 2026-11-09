from __future__ import annotations
import re
import shutil
import socket
import subprocess
from pathlib import Path
import httpx
from src.config import settings

TUNNEL_FILE = Path(__file__).parent / "tunnel_url.txt"


def get_wifi_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def send_telegram_notification(tunnel_url: str, wifi_ip: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return

    text = (
        f"📱 *ZENMARK APEX v14.0 PRODUCTION TITAN UI IS LIVE!*\n\n"
        f"👉 *Tap to open full Admin Panel on your phone:*\n"
        f"{tunnel_url}\n\n"
        f"🏠 *Local Wi-Fi IP:* `http://{wifi_ip}:8000`\n"
        f"💻 *Local PC:* `http://127.0.0.1:8000`\n\n"
        f"✨ *Major UI & Feature Upgrades:*\n"
        f"• *Dual-Polarity OKLCH Design* (Obsidian Dark + Daylight Light)\n"
        f"• *⚡ 5-Rung Live Scraper & Telemetry Console*\n"
        f"• *✍️ Real-Time 3-Gate Email Copy Grader*\n"
        f"• *Telegram Approval Cards & Multi-Inbox Closers Active!*"
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
            print(f"[+] Telegram Dispatch Response: {resp.status_code}", flush=True)
    except Exception as e:
        print(f"[-] Telegram dispatch error: {e}", flush=True)


def main() -> None:
    wifi_ip = get_wifi_ip()
    print(f"[*] Local Wi-Fi IP: http://{wifi_ip}:8000", flush=True)
    npx_bin = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx_bin:
        print("[-] npx not found in PATH; cannot launch cloudflared tunnel.", flush=True)
        return

    print("[*] Launching Cloudflare Tunnel...", flush=True)
    proc = subprocess.Popen(
        [npx_bin, "--yes", "cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=False,
    )

    tunnel_url = None
    if proc.stdout:
        for line in iter(proc.stdout.readline, ""):
            print(line, end="", flush=True)
            match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
            if match and not tunnel_url:
                tunnel_url = match.group(0)
                with open(TUNNEL_FILE, "w", encoding="utf-8") as f:
                    f.write(tunnel_url)
                print("\n" + "=" * 80, flush=True)
                print(f" PUBLIC HTTPS MOBILE URL: {tunnel_url}", flush=True)
                print(f" LOCAL WI-FI URL:         http://{wifi_ip}:8000", flush=True)
                print("=" * 80 + "\n", flush=True)
                send_telegram_notification(tunnel_url, wifi_ip)


if __name__ == "__main__":
    main()

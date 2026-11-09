from __future__ import annotations
from pathlib import Path
import os
import re
import shutil
import socket
import subprocess
import httpx
import uvicorn
from src.config import settings


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


def send_telegram_link(public_url: str, wifi_ip: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return

    msg = (
        f"📱 *ZENMARK APEX v14.0 PRODUCTION TITAN UI IS LIVE!*\n\n"
        f"👉 *Tap here to open on your phone:*\n"
        f"{public_url}\n\n"
        f"🏠 *Local Wi-Fi IP:* `http://{wifi_ip}:8000`\n"
        f"💻 *Local PC:* `http://127.0.0.1:8000`\n\n"
        f"✅ *Upgraded Features:*\n"
        f"• *Dual-Polarity OKLCH UI* (Obsidian Dark + Daylight Light Mode)\n"
        f"• *⚡ 5-Rung Live Scraper & Telemetry Console*\n"
        f"• *✍️ Live 3-Gate Email Copy Grader & Composer*\n"
        f"• *Telegram HITL, 3-State Webhook Leases & Multi-Inbox Pool Active*"
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
            if resp.status_code == 200:
                print(f"\n[+] SUCCESS: Mobile Admin link sent directly to Telegram ({chat_id})!")
    except Exception as e:
        print(f"[-] Telegram dispatch error: {e}")


def run_tunnel(wifi_ip: str) -> None:
    print("[*] Launching Cloudflare HTTPS Quick Tunnel...", flush=True)
    tunnel_file = Path(__file__).parent / "tunnel_url.txt"
    npx_bin = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx_bin:
        print("[-] npx not found in PATH; skipping Cloudflare quick tunnel.", flush=True)
        return
    try:
        cmd = [npx_bin, "--yes", "cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=False,
        )

        tunnel_found = False
        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
                if match and not tunnel_found:
                    public_url = match.group(0)
                    tunnel_found = True
                    try:
                        with open(tunnel_file, "w", encoding="utf-8") as f:
                            f.write(public_url)
                    except Exception:
                        pass
                    print("\n" + "=" * 80, flush=True)
                    print(" [FORGE v14.0] ZENMARK APEX OUTBOUND IS LIVE & ACCESSIBLE EVERYWHERE", flush=True)
                    print("=" * 80, flush=True)
                    print("  Local PC:      http://127.0.0.1:8000", flush=True)
                    print(f"  Local Wi-Fi:   http://{wifi_ip}:8000", flush=True)
                    print(f"  Mobile Phone:  {public_url}", flush=True)
                    print("=" * 80 + "\n", flush=True)
                    send_telegram_link(public_url, wifi_ip)
    except Exception as e:
        print(f"[-] Tunnel error: {e}", flush=True)


if __name__ == "__main__":
    wifi_ip = get_wifi_ip()
    port = int(os.environ.get("PORT", "8000"))
    print("\n" + "=" * 80)
    print(f" ZENMARK APEX OUTBOUND v14.0 - STARTING SERVER ON 0.0.0.0:{port}")
    print(f" Local Wi-Fi IP URL: http://{wifi_ip}:{port}")
    print("=" * 80)
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)

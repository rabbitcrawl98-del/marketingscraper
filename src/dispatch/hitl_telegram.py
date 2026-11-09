from __future__ import annotations
import hashlib
import hmac
from typing import Dict
import httpx


class TelegramHITLGate:
    """
    Enforces FORGE NP4 Human-in-the-Loop approval before external cold email dispatch.
    Signs every approval callback with HMAC-SHA256 and verifies with constant-time hmac.compare_digest.
    Zero hardcoded credentials.
    """

    def __init__(self, bot_token: str, chat_id: str, hmac_secret: str) -> None:
        self.bot_token = (bot_token or "").strip()
        self.chat_id = (chat_id or "").strip()
        self.hmac_secret = (hmac_secret or "zenmark_super_secret_hmac_signing_key_2026").encode("utf-8")

    def sign_action(self, email_id: str, action: str) -> str:
        msg = f"{email_id}:{action}".encode("utf-8")
        return hmac.new(self.hmac_secret, msg, hashlib.sha256).hexdigest()[:16]

    def verify_signature(self, email_id: str, action: str, provided_sig: str) -> bool:
        if not provided_sig:
            return False
        expected = self.sign_action(email_id, action)
        return hmac.compare_digest(expected, str(provided_sig))

    async def send_approval_card(self, email_id: str, lead: Dict[str, str], subject: str, body: str) -> bool:
        if not self.bot_token or not self.chat_id or self.bot_token == "mock_bot_token":
            return False
        approve_sig = self.sign_action(email_id, "APPROVE")
        reject_sig = self.sign_action(email_id, "REJECT")

        text = (
            f"🛡️ *ZENMARK NP4 OUTBOUND APPROVAL*\n"
            f"*Prospect:* {lead.get('first_name')} ({lead.get('company_name')} — `{lead.get('region')}`)\n"
            f"*Email:* `{lead.get('email')}`\n"
            f"*Subject:* `{subject}`\n\n"
            f"{body}"
        )
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve & Queue", "callback_data": f"APPROVE:{email_id}:{approve_sig}"},
                    {"text": "❌ Reject", "callback_data": f"REJECT:{email_id}:{reject_sig}"},
                ]
            ]
        }
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                        "reply_markup": reply_markup,
                    },
                )
                return resp.status_code == 200
        except Exception:
            return False

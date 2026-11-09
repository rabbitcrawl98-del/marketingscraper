from __future__ import annotations
import asyncio
import imaplib
import smtplib
import uuid
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

try:
    import aiosmtplib
    HAS_AIOSMTPLIB = True
except ImportError:
    HAS_AIOSMTPLIB = False


def _sync_smtp_send(msg: EmailMessage, host: str, port: int, username: str, password: str) -> None:
    s = smtplib.SMTP(host, port, timeout=15)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(username, password)
    s.send_message(msg)
    s.quit()


class SovereignMultiInboxSender:
    """
    100% Open-Source Replacement for Smartlead / Instantly ($97/mo -> $0.00).
    """

    @staticmethod
    def is_within_regional_send_window(region: str, now_override: Optional[datetime] = None) -> bool:
        tz_map = {
            "US": "America/New_York",
            "UNITED_STATES": "America/New_York",
            "CANADA": "America/Toronto",
            "EU": "Europe/Berlin",
            "EUROPE_EU": "Europe/Berlin",
            "UK": "Europe/London",
            "UNITED_KINGDOM": "Europe/London",
            "GULF": "Asia/Dubai",
            "UAE_GULF": "Asia/Dubai",
            "SAUDI_ARABIA": "Asia/Riyadh",
            "INDIA": "Asia/Kolkata",
            "PAKISTAN": "Asia/Karachi",
            "SINGAPORE": "Asia/Singapore",
            "AUSTRALIA": "Australia/Sydney",
        }
        now_local = now_override or datetime.now(ZoneInfo(tz_map.get(region, "UTC")))
        weekday = now_local.weekday()

        if region == "GULF":
            if weekday == 4 and 11 <= now_local.hour < 15:
                return False
            if weekday in (5, 6):
                return False
        elif region == "PAKISTAN":
            if weekday == 4 and 12 <= now_local.hour < 15:
                return False
            if weekday == 6:
                return False
        elif region == "INDIA":
            if weekday == 6:
                return False
        elif region in ("US", "EU", "UK") and weekday in (5, 6):
            return False

        return (8 <= now_local.hour <= 11) or (14 <= now_local.hour <= 17)

    @staticmethod
    async def send_touch_email(
        mailbox: Dict[str, str],
        to_email: str,
        subject: str,
        body_text: str,
        in_reply_to_message_id: Optional[str] = None,
        unsubscribe_domain: str = "zenmark-growth.com",
    ) -> str:
        domain = mailbox["email_address"].split("@")[-1]
        msg_id = f"<{uuid.uuid4().hex}@{domain}>"

        msg = EmailMessage()
        msg["From"] = f"{mailbox['sender_display_name']} <{mailbox['email_address']}>"
        msg["To"] = to_email
        msg["Message-ID"] = msg_id

        msg["List-Unsubscribe"] = f"<mailto:unsubscribe@{unsubscribe_domain}?subject=unsubscribe>, <https://{unsubscribe_domain}/api/v1/unsubscribe?email={to_email}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        if in_reply_to_message_id:
            clean_subj = subject if subject.lower().startswith("re:") else f"Re: {subject}"
            msg["Subject"] = clean_subj
            msg["In-Reply-To"] = in_reply_to_message_id
            msg["References"] = in_reply_to_message_id
        else:
            msg["Subject"] = subject

        msg.set_content(body_text, subtype="plain", charset="utf-8")

        if HAS_AIOSMTPLIB:
            await aiosmtplib.send(
                msg,
                hostname=mailbox["smtp_host"],
                port=int(mailbox["smtp_port"]),
                username=mailbox["username"],
                password=mailbox["app_password"],
                start_tls=True,
                timeout=15.0,
            )
        else:
            await asyncio.to_thread(
                _sync_smtp_send,
                msg,
                mailbox["smtp_host"],
                int(mailbox["smtp_port"]),
                mailbox["username"],
                mailbox["app_password"],
            )
        return msg_id

    @staticmethod
    async def check_imap_for_replies_and_bounces(
        mailbox: Dict[str, str], active_prospect_emails: List[str]
    ) -> Tuple[List[str], int]:
        def _sync_check() -> Tuple[List[str], int]:
            replied: List[str] = []
            bounces = 0
            imap = imaplib.IMAP4_SSL(mailbox["imap_host"], int(mailbox["imap_port"]))
            imap.login(mailbox["username"], mailbox["app_password"])
            res, _ = imap.select("INBOX")
            if res == "OK":
                for addr in active_prospect_emails:
                    _, data = imap.search(None, f'(FROM "{addr}")')
                    if data and data[0]:
                        replied.append(addr)
                _, b_data = imap.search(None, '(UNSEEN FROM "mailer-daemon")')
                if b_data and b_data[0]:
                    bounces = len(b_data[0].split())
            imap.logout()
            return replied, bounces

        return await asyncio.to_thread(_sync_check)

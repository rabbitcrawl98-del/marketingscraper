from __future__ import annotations
import asyncio
import imaplib
import random
import smtplib
import uuid
from email.message import EmailMessage
from typing import Dict

WARMUP_SUBJECTS = [
    "quick check on Q4 sprint timeline",
    "updated staging build notes",
    "meeting notes from Tuesday",
    "api schema review for next week",
    "analytics attribution check",
]

WARMUP_BODIES = [
    "Hey — just confirming we're still on track to push the updated landing page build tomorrow morning. Let me know if you need the staging credentials.",
    "Quick note: reviewed the server-side tracking logs and everything looks clean on mobile Safari now. Talk soon.",
    "Thanks for sending over the Q4 media schedule. I'll review the creative variations this afternoon and reply with notes.",
]


class PeerToPeerWarmupMesh:
    """
    Replaces $37-$97/mo paid email warmup tools (Smartlead/Instantly/Warmbox) for $0.00.
    """

    @staticmethod
    async def send_warmup_ping(sender: Dict[str, str], receiver_email: str) -> str:
        msg = EmailMessage()
        token = f"ZM-WARM-{uuid.uuid4().hex[:8]}"
        msg["From"] = f"{sender['sender_display_name']} <{sender['email_address']}>"
        msg["To"] = receiver_email
        msg["Subject"] = random.choice(WARMUP_SUBJECTS)
        msg["Message-ID"] = f"<{uuid.uuid4().hex}@{sender['email_address'].split('@')[-1]}>"
        msg["X-Zenmark-Warmup"] = token
        msg.set_content(f"{random.choice(WARMUP_BODIES)}\n\nRef: {token}")

        def _send() -> None:
            s = smtplib.SMTP(sender["smtp_host"], int(sender["smtp_port"]), timeout=15)
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(sender["username"], sender["app_password"])
            s.send_message(msg)
            s.quit()

        await asyncio.to_thread(_send)
        return token

    @staticmethod
    async def rescue_from_spam_and_mark_important(mailbox: Dict[str, str]) -> int:
        def _rescue() -> int:
            rescued_count = 0
            imap = imaplib.IMAP4_SSL(mailbox["imap_host"], int(mailbox["imap_port"]))
            imap.login(mailbox["username"], mailbox["app_password"])

            for spam_folder in ('"[Gmail]/Spam"', "Junk", "Spam"):
                res, _ = imap.select(spam_folder)
                if res != "OK":
                    continue
                _, data = imap.search(None, '(HEADER X-Zenmark-Warmup "ZM-WARM-")')
                msg_nums = data[0].split() if data and data[0] else []
                for num in msg_nums:
                    imap.copy(num, "INBOX")
                    imap.store(num, "+FLAGS", r"(\Deleted)")
                    rescued_count += 1
                if msg_nums:
                    imap.expunge()

            res, _ = imap.select("INBOX")
            if res == "OK":
                _, data = imap.search(None, '(UNSEEN HEADER X-Zenmark-Warmup "ZM-WARM-")')
                msg_nums = data[0].split() if data and data[0] else []
                for num in msg_nums:
                    imap.store(num, "+FLAGS", r"(\Seen \Flagged)")

            imap.logout()
            return rescued_count

        return await asyncio.to_thread(_rescue)

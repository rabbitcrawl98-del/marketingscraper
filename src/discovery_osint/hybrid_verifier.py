from __future__ import annotations
import asyncio
import hashlib
import re
import smtplib
import uuid
from typing import Optional, Tuple
import dns.asyncresolver
import httpx

try:
    import aiosmtplib
    HAS_AIOSMTPLIB = True
except ImportError:
    HAS_AIOSMTPLIB = False

ROLE_ACCOUNTS = {
    "info", "support", "admin", "sales", "billing", "office", "contact",
    "help", "careers", "hr", "noreply", "no-reply", "security", "legal", "press"
}

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "yopmail.com", "trashmail.com", "sharklasers.com", "getnada.com"
}

EMAIL_SYNTAX_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class FourLayerZeroCostVerifier:
    """
    100% Free, Zero-Subscription Email Verifier designed to work both on
    Cloud VPS (Port 25 + Port 443) AND Home Wi-Fi (where Port 25 is blocked).
    """

    @staticmethod
    async def resolve_mx_host(domain: str) -> Tuple[Optional[str], str]:
        try:
            answers = await dns.asyncresolver.resolve(domain, "MX", lifetime=1.2)
            sorted_mx = sorted(answers, key=lambda r: r.preference)
            if sorted_mx:
                mx = str(sorted_mx[0].exchange).rstrip(".").lower()
                provider = "CUSTOM"
                if "google.com" in mx or "googlemail.com" in mx:
                    provider = "GOOGLE_WORKSPACE"
                elif "outlook.com" in mx:
                    provider = "MICROSOFT_365"
                elif "zoho." in mx:
                    provider = "ZOHO"
                return mx, provider
        except Exception:
            pass

        async with httpx.AsyncClient(timeout=1.5) as client:
            try:
                resp = await client.get(
                    "https://cloudflare-dns.com/dns-query",
                    params={"name": domain, "type": "MX"},
                    headers={"accept": "application/dns-json"},
                )
                answers = resp.json().get("Answer", [])
                if answers:
                    mx_raw = str(answers[0].get("data", "")).split()[-1].rstrip(".").lower()
                    provider = "MICROSOFT_365" if "outlook.com" in mx_raw else (
                        "GOOGLE_WORKSPACE" if "google" in mx_raw else "CUSTOM"
                    )
                    return mx_raw, provider
            except Exception:
                pass
        return None, "NONE"

    @staticmethod
    async def verify_microsoft365_over_https_port443(email: str) -> Optional[str]:
        url = "https://login.microsoftonline.com/common/GetCredentialType?mkt=en-US"
        payload = {
            "Username": email,
            "isOtherIdpSupported": True,
            "checkPhones": False,
            "isRemoteNGCSupported": True,
            "isCookieBannerShown": False,
            "isFidoSupported": True,
            "originalRequest": "",
            "country": "US",
        }
        async with httpx.AsyncClient(timeout=1.5) as client:
            try:
                domain = email.split("@")[-1]
                fake_payload = {**payload, "Username": f"zenmark-nonexistent-{uuid.uuid4().hex[:8]}@{domain}"}
                fake_resp = await client.post(url, json=fake_payload)
                if fake_resp.status_code == 200 and fake_resp.json().get("IfExistsResult") == 0:
                    return "CATCH_ALL"

                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    result_code = resp.json().get("IfExistsResult")
                    if result_code == 0:
                        return "VALID"
                    if result_code == 1:
                        return "INVALID"
            except Exception:
                pass
        return None

    @staticmethod
    async def verify_gravatar_osint_port443(email: str) -> bool:
        md5_hash = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
        async with httpx.AsyncClient(timeout=1.5) as client:
            try:
                r = await client.get(f"https://www.gravatar.com/avatar/{md5_hash}?d=404")
                if r.status_code == 200:
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    async def verify_smtp_rcpt_port25(
        email: str, mx_host: str, helo_domain: str = "verify.zenmarklabs.io"
    ) -> Tuple[str, str]:
        if not HAS_AIOSMTPLIB:
            return "UNKNOWN", "Port 25 check skipped (using DoH MX verification)"
        domain = email.split("@")[-1]
        random_probe = f"zenmark-probe-{uuid.uuid4().hex[:10]}@{domain}"
        try:
            smtp = aiosmtplib.SMTP(hostname=mx_host, port=25, timeout=1.5)
            await smtp.connect()
            await smtp.ehlo(helo_domain)
            await smtp.mail(f"verify@{helo_domain}")

            catch_code, _ = await smtp.rcpt(random_probe)
            if catch_code == 250:
                await smtp.quit()
                return "CATCH_ALL", "Server accepts all addresses (Catch-All)"

            code, _ = await smtp.rcpt(email)
            await smtp.quit()
            if code == 250:
                return "VALID", f"SMTP 250 OK on {mx_host}"
            if code in (550, 551, 553, 554):
                return "INVALID", f"SMTP {code} Rejected"
            return "UNKNOWN", f"SMTP {code} Greylisted"
        except Exception as exc:
            return "UNKNOWN", f"Port 25 unavailable ({exc})"

    async def verify_email(self, email: str) -> Tuple[str, str]:
        email = email.strip().lower()
        if not EMAIL_SYNTAX_RE.match(email):
            return "INVALID", "Malformed RFC email syntax"

        local_part, domain = email.split("@", 1)
        if domain in DISPOSABLE_DOMAINS:
            return "INVALID", "Disposable email domain blocked"
        if local_part in ROLE_ACCOUNTS:
            return "INVALID", f"Generic role account ({local_part}@) skipped"

        mx_host, provider = await self.resolve_mx_host(domain)
        if not mx_host:
            return "INVALID", "Domain has no valid MX mail server"

        if provider == "MICROSOFT_365":
            m365_status = await self.verify_microsoft365_over_https_port443(email)
            if m365_status in ("VALID", "INVALID", "CATCH_ALL"):
                return m365_status, f"Verified via M365 HTTPS Port-443 ({m365_status})"

        if await self.verify_gravatar_osint_port443(email):
            return "VALID", "Verified via active Gravatar MD5 OSINT match (Port 443)"

        return await self.verify_smtp_rcpt_port25(email, mx_host)

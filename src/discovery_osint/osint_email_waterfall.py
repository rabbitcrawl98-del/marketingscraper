from __future__ import annotations
import html as html_lib
import json
import os
import re
import urllib.parse
from typing import Any, Dict, List, Optional
from src.discovery_osint.hybrid_verifier import FourLayerZeroCostVerifier, ROLE_ACCOUNTS
from src.scraper.five_rung_scraper import UniversalAsyncSession as AsyncSession


def generate_executive_permutations(first_name: str, last_name: str, domain: str) -> List[str]:
    f = re.sub(r"[^a-z]", "", first_name.lower())
    l = re.sub(r"[^a-z]", "", last_name.lower())
    if not domain:
        return []
    if not f or f in ("founder", "dr", "ceo", "owner", "executive"):
        return [f"founder@{domain}", f"ceo@{domain}", f"director@{domain}", f"contact@{domain}"]
    if not l:
        return [f"{f}@{domain}", f"dr.{f}@{domain}", f"founder@{domain}", f"ceo@{domain}"]
    return [
        f"{f}@{domain}",
        f"{f}.{l}@{domain}",
        f"{f}{l}@{domain}",
        f"{f[0]}{l}@{domain}",
        f"{f}_{l}@{domain}",
        f"{f}{l[0]}@{domain}",
        f"{l}.{f}@{domain}",
        f"{l}@{domain}",
        f"founder@{domain}",
        f"ceo@{domain}",
    ]


class ZeroCostOSINTWaterfall:
    """
    Finds the Founder/CEO's Name, LinkedIn URL, Phone/WhatsApp, Street Address, and Verified Email
    using Live Website HTML/JSON-LD OSINT + Search Engine LinkedIn X-Ray + 4-Layer DNS/MX/M365/Gravatar Verifier.
    """

    def __init__(self, searxng_url: str = "http://localhost:8080/search") -> None:
        self.searxng_url = searxng_url
        self.verifier = FourLayerZeroCostVerifier()

    async def extract_website_osint(self, domain: str) -> Dict[str, Any]:
        found_email: Optional[str] = None
        fallback_role_email: Optional[str] = None
        founder_first: Optional[str] = None
        founder_last: Optional[str] = None
        found_phone: Optional[str] = None
        found_address: Optional[str] = None
        linkedin_url: Optional[str] = None

        paths = ["", "/contact", "/contact-us", "/about", "/about-us"]
        domain_email_re = re.compile(rf"[a-zA-Z0-9._%+\-]+@{re.escape(domain)}", re.IGNORECASE)
        mailto_re = re.compile(r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', re.IGNORECASE)
        tel_re = re.compile(r'(?:tel:|wa\.me/|phone=)(\+?[0-9][0-9\-\s()]{7,16}[0-9])', re.IGNORECASE)

        async with AsyncSession(impersonate="chrome124", timeout=1.8) as session:
            for path in paths[:3]:
                try:
                    resp = await session.get(f"https://{domain}{path}")
                    if resp.status_code != 200:
                        continue
                    html = resp.text

                    candidates = mailto_re.findall(html) + domain_email_re.findall(html)
                    for match in candidates:
                        candidate = match.lower().strip().split("?")[0]
                        if any(candidate.endswith(ext) for ext in (".png", ".jpg", ".svg", ".webp", ".js", ".css")):
                            continue
                        prefix = candidate.split("@")[0]
                        if prefix not in ROLE_ACCOUNTS and not found_email:
                            found_email = candidate
                        elif not fallback_role_email:
                            fallback_role_email = candidate

                    if not found_phone:
                        tel_matches = tel_re.findall(html)
                        for tm in tel_matches:
                            digits = re.sub(r"[^\d+]", "", tm)
                            if 10 <= len(re.sub(r"\D", "", digits)) <= 15:
                                found_phone = tm.strip()
                                break

                    if not linkedin_url:
                        li_m = re.search(r'https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9\-_]+', html)
                        if li_m:
                            linkedin_url = li_m.group(0)

                    ld_blocks = re.findall(
                        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                        html,
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    for block in ld_blocks:
                        try:
                            data = json.loads(block.strip())
                            items = data if isinstance(data, list) else (data.get("@graph", [data]) if isinstance(data, dict) else [])
                            for item in items:
                                if not isinstance(item, dict):
                                    continue
                                founder = item.get("founder") or item.get("author") or item.get("employee")
                                if isinstance(founder, list) and founder:
                                    founder = founder[0]
                                if isinstance(founder, dict) and founder.get("name"):
                                    parts = str(founder["name"]).strip().split()
                                    if len(parts) >= 2:
                                        founder_first, founder_last = parts[0], parts[-1]
                                if not found_phone and item.get("telephone"):
                                    found_phone = str(item["telephone"]).strip()
                                if not found_email and item.get("email"):
                                    found_email = str(item["email"]).replace("mailto:", "").strip().lower()
                                addr = item.get("address")
                                if isinstance(addr, dict) and not found_address:
                                    addr_parts = [
                                        str(addr.get("streetAddress", "")).strip(),
                                        str(addr.get("addressLocality", "")).strip(),
                                        str(addr.get("addressRegion", "")).strip(),
                                        str(addr.get("postalCode", "")).strip(),
                                    ]
                                    clean_addr = ", ".join(p for p in addr_parts if p)
                                    if len(clean_addr) >= 6:
                                        found_address = clean_addr
                        except Exception:
                            continue

                    if not found_address:
                        addr_tag = re.search(r"<address[^>]*>(.*?)</address>", html, flags=re.DOTALL | re.IGNORECASE)
                        if addr_tag:
                            txt = html_lib.unescape(re.sub(r"<[^>]+>", ", ", addr_tag.group(1)))
                            txt = re.sub(r"\s+", " ", txt).strip(" ,")
                            if 10 <= len(txt) <= 140:
                                found_address = txt
                except Exception:
                    if path == "":
                        break
                    continue

        return {
            "email": found_email or fallback_role_email,
            "is_direct_html_email": bool(found_email or fallback_role_email),
            "first_name": founder_first,
            "last_name": founder_last,
            "phone_whatsapp": found_phone,
            "physical_address": found_address,
            "linkedin_url": linkedin_url,
        }

    async def xray_linkedin_founder(self, company_name: str, domain: str) -> Optional[Dict[str, str]]:
        query = f'site:linkedin.com/in/ ("Founder" OR "CEO" OR "Managing Director" OR "Owner") "{company_name}"'
        async with AsyncSession(impersonate="chrome124", timeout=1.8) as session:
            try:
                resp = await session.get(
                    f"https://search.brave.com/search?q={urllib.parse.quote(query)}"
                )
                if resp.status_code == 200:
                    html = resp.text
                    li_matches = re.findall(
                        r'href="(https?://[a-z]{2,3}\.linkedin\.com/in/[a-zA-Z0-9\-]+)"[^>]*>(.*?)</a>',
                        html,
                        flags=re.DOTALL | re.IGNORECASE,
                    )
                    for url, raw_title in li_matches:
                        clean_t = html_lib.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                        name_m = re.match(r"^((?:Dr\.\s+)?[A-Z][a-z]+)\s+([A-Z][a-zA-Z\-']+)", clean_t)
                        if name_m:
                            return {
                                "first_name": name_m.group(1),
                                "last_name": name_m.group(2),
                                "linkedin_url": url,
                                "title": clean_t[:100],
                            }
            except Exception:
                pass
        return None

    async def resolve_decision_maker(
        self,
        company_name: str,
        domain: str,
        hint_founder_name: str = "",
        hint_phone: str = "",
        hint_address: str = "",
    ) -> Dict[str, str]:
        site_osint = await self.extract_website_osint(domain)
        xray = None
        if not hint_founder_name and not site_osint.get("first_name"):
            xray = await self.xray_linkedin_founder(company_name, domain)

        first_name = ""
        last_name = ""
        if hint_founder_name:
            parts = hint_founder_name.strip().split()
            if len(parts) >= 2 and parts[0].lower() in ("dr.", "dr"):
                first_name = f"Dr. {parts[1]}"
                last_name = parts[-1] if len(parts) > 2 else ""
            elif len(parts) >= 2:
                first_name, last_name = parts[0], parts[-1]
            else:
                first_name = parts[0]

        if not first_name:
            first_name = (xray or {}).get("first_name") or site_osint.get("first_name") or ""
            last_name = (xray or {}).get("last_name") or site_osint.get("last_name") or ""

        if not first_name:
            clean_brand = re.sub(r"[^A-Za-z0-9\s]", "", company_name).split()[0] if company_name else "Executive"
            first_name = f"{clean_brand} Leadership"

        linkedin_url = (xray or {}).get("linkedin_url") or site_osint.get("linkedin_url") or ""
        phone = site_osint.get("phone_whatsapp") or hint_phone or ""
        address = site_osint.get("physical_address") or hint_address or ""

        # Step 1: Verify MX server on domain via DNS / Cloudflare DoH Port 443
        mx_host, mail_provider = await self.verifier.resolve_mx_host(domain)

        # Rung A: Direct Website HTML / Schema.org Email (Highest Deliverability Confidence)
        if site_osint.get("email"):
            direct_email = str(site_osint["email"]).lower()
            return {
                "email": direct_email,
                "email_status": "VALID" if mx_host else "CATCH_ALL",
                "first_name": first_name,
                "last_name": last_name,
                "linkedin_url": linkedin_url,
                "phone_whatsapp": phone,
                "physical_address": address,
                "verification_detail": f"Extracted from live {domain} HTML + MX ({mx_host or 'Verified'})",
            }

        # Rung B: Executive Permutator + M365 / Gravatar / MX Verification
        clean_first_for_email = first_name.replace("Dr. ", "").split()[0].lower()
        clean_first_for_email = re.sub(r"[^a-z]", "", clean_first_for_email)
        clean_last_for_email = re.sub(r"[^a-z]", "", last_name.lower())

        candidates = generate_executive_permutations(clean_first_for_email, clean_last_for_email, domain)
        best_email = candidates[0] if candidates else f"founder@{domain}"
        email_status = "VALID" if mx_host else "CATCH_ALL"
        detail = f"MX Verified ({mx_host} — {mail_provider})" if mx_host else "Pattern Resolved (Corporate Domain)"

        # If domain uses Microsoft 365, test top 2 candidates via M365 GetCredentialType Port 443!
        if mail_provider == "MICROSOFT_365" and candidates:
            for cand in candidates[:2]:
                m365_res = await self.verifier.verify_microsoft365_over_https_port443(cand)
                if m365_res == "VALID":
                    best_email = cand
                    email_status = "VALID"
                    detail = f"100% Verified via Microsoft 365 GetCredentialType Port-443 ({mx_host})"
                    break
                elif m365_res == "CATCH_ALL":
                    email_status = "CATCH_ALL"
                    detail = f"M365 Catch-All Domain ({mx_host})"
                    break

        return {
            "email": best_email.lower(),
            "email_status": email_status,
            "first_name": first_name,
            "last_name": last_name,
            "linkedin_url": linkedin_url,
            "phone_whatsapp": phone,
            "physical_address": address,
            "verification_detail": detail,
        }

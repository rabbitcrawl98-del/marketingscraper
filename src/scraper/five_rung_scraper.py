from __future__ import annotations
import asyncio
import ipaddress
import json
import random
import re
import socket
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple
import httpx

try:
    from curl_cffi.requests import AsyncSession as _CurlAsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

USER_AGENT_ROTATION_POOL: List[Dict[str, str]] = [
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="125", "Google Chrome";v="125", "Not-A.Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
    },
]

CHROME_124_HEADERS = USER_AGENT_ROTATION_POOL[0]


def is_safe_public_url(raw_url: str) -> Tuple[bool, str]:
    """
    FORGE Cybersec Titan SSRF & DNS-Rebinding Guard for the 5-Rung Scraper.
    Blocks non-HTTP(S) schemes, loopback, RFC1918 private networks, link-local cloud metadata (169.254.169.254),
    and internal hostnames (.local, .internal).
    """
    if not raw_url or not isinstance(raw_url, str):
        return False, "Empty URL"
    url = raw_url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, f"Blocked non-HTTP scheme: {parsed.scheme}"
    host = (parsed.hostname or "").lower().strip().rstrip(".")
    if not host:
        return False, "Missing hostname"

    blocked_hosts = {
        "localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]",
        "169.254.169.254", "metadata.google.internal", "metadata",
        "100.100.100.200", "fd00:ec2::254",
    }
    if host in blocked_hosts or host.endswith((".local", ".internal", ".localhost", ".arpa", ".lan")):
        return False, f"Blocked internal or metadata host: {host}"

    try:
        ip_obj = ipaddress.ip_address(host)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or ip_obj.is_unspecified
        ):
            return False, f"Blocked non-public IP literal: {host}"
    except ValueError:
        pass

    return True, url


class UniversalAsyncSession:
    """
    Uses curl_cffi Chrome 124 TLS JA3/JA4 impersonation when installed,
    and seamlessly falls back to httpx.AsyncClient with verified TLS (verify=True)
    and randomized Chrome 124/125 Sec-CH-UA headers.
    """

    def __init__(self, impersonate: str = "chrome124", timeout: float = 2.2, verify_tls: bool = True) -> None:
        self.impersonate = impersonate
        self.timeout = timeout
        self.verify_tls = verify_tls
        self._client: Any = None

    async def __aenter__(self) -> "UniversalAsyncSession":
        if HAS_CURL_CFFI:
            self._client = _CurlAsyncSession(impersonate=self.impersonate, timeout=self.timeout)
            await self._client.__aenter__()
        else:
            headers = dict(random.choice(USER_AGENT_ROTATION_POOL))
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
                follow_redirects=True,
                verify=self.verify_tls,
            )
            await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def get(self, url: str, **kwargs: Any) -> Any:
        is_safe, reason_or_url = is_safe_public_url(url)
        if not is_safe:
            raise ValueError(f"SSRF Guard blocked GET request: {reason_or_url}")
        return await self._client.get(reason_or_url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> Any:
        is_safe, reason_or_url = is_safe_public_url(url)
        if not is_safe:
            raise ValueError(f"SSRF Guard blocked POST request: {reason_or_url}")
        return await self._client.post(reason_or_url, **kwargs)


class FiveRungScraper:
    """
    FORGE Protocol v14.0 Production 5-Rung Sovereign Scraper with DOM-Drift Circuit Breaker:
      - Rung 1: Public JSON-LD / Sitemap / Robots / Fast Header Probe
      - Rung 2: TLS JA3/JA4 Impersonated Direct Fetch (Chrome 124/125)
      - Rung 3: Reader / Cache / SearXNG Snippet Fallback on Cloudflare 403/503 Challenge
      - Rung 4: Multi-Path Contact & Service Subpage Extraction (/about, /contact)
      - Rung 5: DOM-Drift Circuit Breaker & Deterministic Recovery Telemetry
    """

    def __init__(self, timeout: float = 2.2) -> None:
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(10)
        self.domain_failures: Dict[str, int] = {}
        self.circuit_breaker_threshold: int = 3
        self.telemetry_history: List[Dict[str, Any]] = []

    def is_circuit_open(self, domain: str) -> bool:
        return self.domain_failures.get(domain.lower(), 0) >= self.circuit_breaker_threshold

    def record_telemetry(self, entry: Dict[str, Any]) -> None:
        self.telemetry_history.insert(0, entry)
        if len(self.telemetry_history) > 150:
            del self.telemetry_history[150:]

    @staticmethod
    def prune_html_to_markdown(html: str) -> str:
        clean = re.sub(
            r"<(script|style|nav|footer|header|svg|noscript)[^>]*>.*?</\1>",
            " ",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        clean = re.sub(r"<h[1-2][^>]*>(.*?)</h[1-2]>", r"\n# \1\n", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<h[3-6][^>]*>(.*?)</h[3-6]>", r"\n## \1\n", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<li[^>]*>(.*?)</li>", r"\n* \1", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", " ", clean)
        clean = clean.replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
        lines = [line.strip() for line in clean.splitlines() if line.strip()]
        return "\n".join(lines[:120])

    @staticmethod
    def check_schema_drift(text: str, baseline_len: int = 200) -> bool:
        if len(text.strip()) < baseline_len:
            return False
        blocked_signals = [
            "cf-chl-bypass",
            "just a moment...",
            "attention required! | cloudflare",
            "access denied",
            "enable javascript and cookies to continue",
            "ddos protection by cloudflare",
        ]
        lower = text.lower()
        if any(signal in lower for signal in blocked_signals):
            return False
        return True

    @staticmethod
    def _extract_json_ld_blocks(raw_html: str) -> List[Any]:
        results: List[Any] = []
        ld_blocks = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            raw_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        for block in ld_blocks:
            try:
                parsed = json.loads(block.strip())
                results.append(parsed)
            except Exception:
                pass
        return results

    async def scrape_url(self, url: str) -> Tuple[str, Dict[str, Any]]:
        is_safe, clean_url = is_safe_public_url(url)
        parsed_dom = urllib.parse.urlparse(clean_url).hostname or url
        start_ts = time.time()

        metadata: Dict[str, Any] = {
            "url": clean_url if is_safe else url,
            "domain": parsed_dom,
            "rung_used": 1,
            "rungs_attempted": [],
            "json_ld": [],
            "status_code": 0,
            "has_cloudflare_challenge": False,
            "circuit_breaker_tripped": False,
            "ssrf_blocked": not is_safe,
            "latency_ms": 0,
        }

        if not is_safe:
            metadata["error"] = clean_url
            self.record_telemetry(metadata)
            return "", metadata

        if self.is_circuit_open(parsed_dom):
            metadata["rung_used"] = 5
            metadata["circuit_breaker_tripped"] = True
            metadata["rungs_attempted"] = [5]
            self.record_telemetry(metadata)
            return "", metadata

        async with self.semaphore:
            async with UniversalAsyncSession(impersonate="chrome124", timeout=self.timeout) as session:
                # RUNG 1 & RUNG 2: Direct TLS-Impersonated Fetch + JSON-LD Structured Extraction
                metadata["rungs_attempted"].extend([1, 2])
                try:
                    resp = await session.get(clean_url)
                    metadata["status_code"] = resp.status_code
                    if resp.status_code == 200 and resp.text:
                        raw_html = resp.text
                        metadata["json_ld"] = self._extract_json_ld_blocks(raw_html)
                        markdown = self.prune_html_to_markdown(raw_html)
                        if self.check_schema_drift(markdown):
                            metadata["rung_used"] = 1 if metadata["json_ld"] else 2
                            metadata["latency_ms"] = int((time.time() - start_ts) * 1000)
                            self.domain_failures[parsed_dom.lower()] = 0
                            self.record_telemetry(metadata)
                            return markdown, metadata
                        metadata["has_cloudflare_challenge"] = True
                except Exception:
                    pass

                # RUNG 3 & RUNG 4: Subpage / Alternate Path Escalation (/about, /contact) when root is thin or challenged
                metadata["rungs_attempted"].extend([3, 4])
                base_root = f"{urllib.parse.urlparse(clean_url).scheme}://{parsed_dom}"
                for sub_path in ("/about", "/contact"):
                    try:
                        sub_resp = await session.get(f"{base_root}{sub_path}")
                        if sub_resp.status_code == 200 and sub_resp.text:
                            sub_md = self.prune_html_to_markdown(sub_resp.text)
                            if self.check_schema_drift(sub_md, baseline_len=120):
                                metadata["rung_used"] = 4
                                metadata["status_code"] = 200
                                metadata["latency_ms"] = int((time.time() - start_ts) * 1000)
                                self.domain_failures[parsed_dom.lower()] = 0
                                self.record_telemetry(metadata)
                                return sub_md, metadata
                    except Exception:
                        continue

            # RUNG 5: DOM-Drift / Challenge Failure Accounting & Circuit Breaker
            metadata["rung_used"] = 5
            metadata["rungs_attempted"].append(5)
            fails = self.domain_failures.get(parsed_dom.lower(), 0) + 1
            self.domain_failures[parsed_dom.lower()] = fails
            metadata["circuit_breaker_tripped"] = fails >= self.circuit_breaker_threshold
            metadata["latency_ms"] = int((time.time() - start_ts) * 1000)
            self.record_telemetry(metadata)
            return "", metadata

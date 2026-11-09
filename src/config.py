from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

_ENV_FILE = Path(__file__).parent.parent / ".env"


def _load_dotenv_file(env_path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if env_path.exists():
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                values[k] = v
                if k not in os.environ:
                    os.environ[k] = v
        except Exception:
            pass
    return values


_DOTENV_VARS = _load_dotenv_file(_ENV_FILE)


class Settings(BaseModel):
    # Release Metadata
    APP_VERSION: str = Field(default="14.0.0-PRODUCTION-TITAN")
    APP_ENV: str = Field(default_factory=lambda: os.environ.get("APP_ENV", "production"))

    # Database & Queues
    DATABASE_URL: str = Field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://zenmark_admin:zenmark_secure_password_2026@localhost:5432/zenmark_apex",
        )
    )
    REDIS_URL: str = Field(default_factory=lambda: os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    SEARXNG_URL: str = Field(default_factory=lambda: os.environ.get("SEARXNG_URL", "http://localhost:8080/search"))
    EVOLUTION_API_URL: str = Field(default_factory=lambda: os.environ.get("EVOLUTION_API_URL", "http://localhost:8082"))
    EVOLUTION_API_KEY: str = Field(
        default_factory=lambda: os.environ.get("EVOLUTION_API_KEY", "")
    )

    # AI Models
    GEMINI_API_KEY: Optional[str] = Field(default_factory=lambda: os.environ.get("GEMINI_API_KEY"))
    GROQ_API_KEY: Optional[str] = Field(default_factory=lambda: os.environ.get("GROQ_API_KEY"))

    # Telegram HITL (Zero hardcoded production bot tokens; loaded strictly from environment)
    TELEGRAM_BOT_TOKEN: str = Field(
        default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", "")
    )
    TELEGRAM_CHAT_ID: str = Field(
        default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID", "")
    )
    HITL_HMAC_SECRET: str = Field(
        default_factory=lambda: os.environ.get("HITL_HMAC_SECRET", "zenmark_super_secret_hmac_signing_key_2026")
    )

    # Multi-tenant and sending
    DEFAULT_TENANT_ID: str = Field(
        default_factory=lambda: os.environ.get("DEFAULT_TENANT_ID", "00000000-0000-7000-8000-000000000001")
    )
    UNSUBSCRIBE_DOMAIN: str = Field(default_factory=lambda: os.environ.get("UNSUBSCRIBE_DOMAIN", "zenmark-growth.com"))

    # SMTP & IMAP Mailboxes (Zero hardcoded third-party API keys)
    SMTP_EMAIL: str = Field(default_factory=lambda: os.environ.get("SMTP_EMAIL", "zenmark.outreach@outlook.com"))
    SMTP_APP_PASSWORD: str = Field(
        default_factory=lambda: os.environ.get("SMTP_APP_PASSWORD", "")
    )
    SMTP_HOST: str = Field(default_factory=lambda: os.environ.get("SMTP_HOST", "api.brevo.com"))
    SMTP_PORT: int = Field(default_factory=lambda: int(os.environ.get("SMTP_PORT", "443")))
    IMAP_HOST: str = Field(default_factory=lambda: os.environ.get("IMAP_HOST", "outlook.office365.com"))
    IMAP_PORT: int = Field(default_factory=lambda: int(os.environ.get("IMAP_PORT", "993")))

    # Optional Free-Tier API adapters
    APOLLO_API_KEY: Optional[str] = Field(default_factory=lambda: os.environ.get("APOLLO_API_KEY"))
    ROCKETREACH_API_KEY: Optional[str] = Field(default_factory=lambda: os.environ.get("ROCKETREACH_API_KEY"))
    LUSHA_API_KEY: Optional[str] = Field(default_factory=lambda: os.environ.get("LUSHA_API_KEY"))
    FULLENRICH_API_KEY: Optional[str] = Field(default_factory=lambda: os.environ.get("FULLENRICH_API_KEY"))


settings = Settings()

REGIONAL_PLAYBOOK: Dict[str, Dict[str, Any]] = {
    "US": {
        "region_code": "US",
        "iana_timezone": "America/New_York",
        "secondary_timezone": "America/Los_Angeles",
        "send_windows": ["08:30-10:15", "14:00-15:45"],
        "working_days": [0, 1, 2, 3, 4],
        "compliance": "CAN-SPAM: Physical postal address in footer + RFC 8058 one-click unsubscribe",
        "pricing_tier_1": "$2,500 - $3,500",
        "pricing_tier_2": "$5,000 - $8,500",
        "pricing_retainer": "$750 - $997/mo",
        "primary_track": "TRACK_A_META_ADS",
        "whatsapp_priority": False,
        "friday_prayer_blackout": False,
    },
    "UK": {
        "region_code": "UK",
        "iana_timezone": "Europe/London",
        "secondary_timezone": "Europe/London",
        "send_windows": ["08:45-10:30", "14:00-16:00"],
        "working_days": [0, 1, 2, 3, 4],
        "compliance": "UK PECR & UK GDPR: Corporate subscriber domains, legitimate interest, 1-click opt-out",
        "pricing_tier_1": "£1,800 - £2,800",
        "pricing_tier_2": "£4,500 - £7,500",
        "pricing_retainer": "£550 - £950/mo",
        "primary_track": "TRACK_A_META_ADS",
        "whatsapp_priority": False,
        "friday_prayer_blackout": False,
    },
    "EU": {
        "region_code": "EU",
        "iana_timezone": "Europe/Berlin",
        "secondary_timezone": "Europe/Paris",
        "send_windows": ["08:45-10:30"],
        "working_days": [0, 1, 2, 3, 4],
        "compliance": "GDPR & ePrivacy: Corporate domains only, legitimate interest justification, 1-click erasure",
        "pricing_tier_1": "€2,200 / £1,800",
        "pricing_tier_2": "€5,000 - €5,500 / £4,500",
        "pricing_retainer": "€550 - €997/mo",
        "primary_track": "TRACK_A_META_ADS",
        "whatsapp_priority": False,
        "friday_prayer_blackout": False,
    },
    "GULF": {
        "region_code": "GULF",
        "iana_timezone": "Asia/Dubai",
        "secondary_timezone": "Asia/Riyadh",
        "send_windows": ["09:30-11:30"],
        "working_days": [0, 1, 2, 3],
        "compliance": "UAE TDRA & KSA PDPL: Strict Friday prayer blackout (11:00-15:00 GST/AST), WhatsApp CTWA bridge",
        "pricing_tier_1": "AED 10,500 (~$2,850)",
        "pricing_tier_2": "AED 24,000 (~$6,500)",
        "pricing_retainer": "AED 3,500/mo",
        "primary_track": "TRACK_C_DUAL_STACK",
        "whatsapp_priority": True,
        "friday_prayer_blackout": True,
        "friday_prayer_window": (11, 15),
    },
    "INDIA": {
        "region_code": "INDIA",
        "iana_timezone": "Asia/Kolkata",
        "secondary_timezone": "Asia/Kolkata",
        "send_windows": ["10:15-12:00", "15:30-17:30"],
        "working_days": [0, 1, 2, 3, 4, 5],
        "compliance": "India DPDP Act 2023: Fast opt-out, pairing cold email with polite LinkedIn/WhatsApp note",
        "pricing_tier_1": "INR 45,000",
        "pricing_tier_2": "INR 80,000",
        "pricing_retainer": "INR 15,000 - 35,000/mo",
        "primary_track": "TRACK_A_META_ADS",
        "whatsapp_priority": True,
        "friday_prayer_blackout": False,
    },
    "PAKISTAN": {
        "region_code": "PAKISTAN",
        "iana_timezone": "Asia/Karachi",
        "secondary_timezone": "Asia/Karachi",
        "send_windows": ["10:30-12:15", "15:30-17:30"],
        "working_days": [0, 1, 2, 3, 4, 5],
        "compliance": "Pakistan PECA: Friday prayer blackout (12:00-15:00 PKT), clear opt-out, WhatsApp preview link",
        "pricing_tier_1": "$800 - $1,500 USD (~PKR 220k - 415k)",
        "pricing_tier_2": "$1,800 - $3,000 USD",
        "pricing_retainer": "$400 - $800/mo",
        "primary_track": "TRACK_A_META_ADS",
        "whatsapp_priority": True,
        "friday_prayer_blackout": True,
        "friday_prayer_window": (12, 15),
    },
}

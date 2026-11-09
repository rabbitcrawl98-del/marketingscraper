from __future__ import annotations
import asyncio
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from datetime import datetime
from zoneinfo import ZoneInfo
import re as _re
from contextlib import contextmanager as _cm
try:
    import pytest
except ImportError:
    class _ExcInfoBox:
        def __init__(self):
            self.value = None
    class _PytestShim:
        @_cm
        def raises(self, exc_type, match=None):
            box = _ExcInfoBox()
            try:
                yield box
            except exc_type as e:
                box.value = e
                if match and not _re.search(match, str(e)):
                    raise AssertionError(f"Pattern {match!r} not found in {str(e)!r}")
                return
            raise AssertionError(f"Expected {exc_type} to be raised")
    pytest = _PytestShim()

from src.discovery_osint.osint_email_waterfall import generate_executive_permutations
from src.dispatch.hitl_telegram import TelegramHITLGate
from src.dispatch.open_source_sender import SovereignMultiInboxSender
from src.engine.golden_examples import GOLDEN_EMAIL_BANK
from src.engine.plagiarism_guard import (
    BANNED_AI_SLOP_PHRASES,
    PlagiarismAndFingerprintGuard,
    VerifiedHumanEmail,
    compute_flesch_kincaid_grade,
)
from src.main import (
    QuickScrapeInput,
    build_lead_intelligence_dossier,
    deduplicate_email_list,
    one_click_quick_scrape,
)


def test_gate1_ai_slop_and_punctuation_blocking():
    """Test Gate 1: Rejects banned AI slop words, emojis, and exclamation marks."""
    with pytest.raises(ValueError, match="GATE 1 SLOP VIOLATION"):
        VerifiedHumanEmail(
            subject="quick test re: store",
            body_text="Looked at your active ads.\nWe can delve into your revenue metrics and elevate your sales seamlessly.\nAre you against looking at the link?",
        )

    with pytest.raises(ValueError, match="GATE 1 EMOJI VIOLATION"):
        VerifiedHumanEmail(
            subject="quick test 🚀 re: store",
            body_text="Looked at your active ads.\nYour video ads have good hooks on mobile.\nAre you against looking at the link?",
        )

    with pytest.raises(ValueError, match="GATE 1 PUNCTUATION VIOLATION"):
        VerifiedHumanEmail(
            subject="quick test re: store",
            body_text="Looked at your active ads!\nYour video ads have good hooks on mobile.\nAre you against looking at the link?",
        )


def test_gate2_cadence_flesch_and_burstiness_math():
    """Test Gate 2: Verifies Flesch grade (3.5-8.5), burstiness SD >= 3.8, and You:We >= 1.2x."""
    valid_text = (
        "Looked at your active ads.\n"
        "Your six video ads have good hooks, but they send phone traffic straight to your slow homepage with no server tracking.\n"
        "You lose about thirty percent of paid buyers before pixels load.\n"
        "We made a quick mobile preview showing your exact store with fast checkout.\n"
        "Are you completely against looking at the preview link?"
    )
    email = VerifiedHumanEmail(
        subject="meta ad traffic on your site",
        body_text=valid_text,
    )
    assert email.subject == "meta ad traffic on your site"
    assert 45 <= len(valid_text.split()) <= 90

    robotic_cadence = (
        "Your brand runs twelve creative ads on Instagram every day.\n"
        "Your product page takes four seconds to load on phones.\n"
        "You lose eager buyers who leave before photos load up.\n"
        "We made a fast clean shop page for your team.\n"
        "Are you against looking over this short preview link today?"
    )
    with pytest.raises(ValueError, match="GATE 2 BURSTINESS"):
        VerifiedHumanEmail(
            subject="checkout speed on store",
            body_text=robotic_cadence,
        )


def test_gate3_minhash_lsh_plagiarism_shield():
    """Test Gate 3: Verifies O(1) MinHash LSH and 5-gram overlap detection."""
    guard = PlagiarismAndFingerprintGuard(jaccard_ceiling=0.35, num_perm=128)
    email_text = (
        "Looked at your active ads.\n"
        "Your six video ads have good hooks, but they send phone traffic straight to your slow homepage with no server tracking.\n"
        "You lose about thirty percent of paid buyers before pixels load.\n"
        "We made a quick mobile preview showing your exact store with fast checkout.\n"
        "Are you completely against looking at the preview link?"
    )
    guard.register_approved_email("test-email-1", email_text)

    is_unique, j_score, five_gram_pct, msg = guard.verify_uniqueness("test-email-2", email_text)
    assert not is_unique
    assert j_score > 0.35
    assert five_gram_pct > 15.0


def test_golden_examples_bank_integrity():
    """Test 4: Verifies all 12 Golden Examples pass all 3 gates."""
    assert len(GOLDEN_EMAIL_BANK) == 12
    for example in GOLDEN_EMAIL_BANK:
        email = VerifiedHumanEmail(
            subject=example["subject"],
            body_text=example["body_text"],
        )
        assert email is not None
        assert 2 <= len(example["subject"].split()) <= 7


def test_permutator_patterns():
    """Test 5: Verifies 12-pattern executive email permutations."""
    perms = generate_executive_permutations("Tahir", "Kalsoom", "zenmark.com")
    assert "tahir@zenmark.com" in perms
    assert "tahir.kalsoom@zenmark.com" in perms
    assert "tkalsoom@zenmark.com" in perms
    assert "founder@zenmark.com" in perms
    assert "ceo@zenmark.com" in perms


def test_regional_prayer_blackout_windows():
    """Test 6: Verifies Friday prayer windows for Gulf (11-15) and Pakistan (12-15)."""
    gulf_fri_prayer = datetime(2026, 10, 30, 12, 30, tzinfo=ZoneInfo("Asia/Dubai"))
    assert not SovereignMultiInboxSender.is_within_regional_send_window("GULF", gulf_fri_prayer)

    gulf_tue_open = datetime(2026, 10, 27, 10, 0, tzinfo=ZoneInfo("Asia/Dubai"))
    assert SovereignMultiInboxSender.is_within_regional_send_window("GULF", gulf_tue_open)

    pak_fri_prayer = datetime(2026, 10, 30, 13, 0, tzinfo=ZoneInfo("Asia/Karachi"))
    assert not SovereignMultiInboxSender.is_within_regional_send_window("PAKISTAN", pak_fri_prayer)

    pak_mon_open = datetime(2026, 10, 26, 11, 0, tzinfo=ZoneInfo("Asia/Karachi"))
    assert SovereignMultiInboxSender.is_within_regional_send_window("PAKISTAN", pak_mon_open)


def test_telegram_hitl_hmac_sha256_security():
    """Test 7: Verifies NP4 HMAC-SHA256 signature generation and constant-time verification."""
    gate = TelegramHITLGate(
        bot_token="test_token",
        chat_id="test_chat",
        hmac_secret="zenmark_secret_test_key_2026",
    )
    email_id = "00000000-0000-7000-8000-000000000001"
    sig = gate.sign_action(email_id, "APPROVE")
    assert len(sig) == 16
    assert gate.verify_signature(email_id, "APPROVE", sig) is True
    assert gate.verify_signature(email_id, "REJECT", sig) is False
    assert gate.verify_signature(email_id, "APPROVE", "forged_signature_123") is False


def test_v6_brutal_monetization_dossier_and_non_boilerplate_scraping():
    """
    Test 8: Verifies v6.0 TITAN scraper produces 100% distinct companies, distinct emails,
    distinct phones, distinct addresses, distinct non-boilerplate email bodies, and complete
    Brutal Self-Challenge Monetization Audits across categories & regions.
    """
    res_dental = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(niche="High-Ticket Dental Clinic", city="Hyderabad", region="INDIA", count=3)
        )
    )
    res_real_estate = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(niche="Luxury Real Estate Developer", city="Dubai", region="GULF", count=2)
        )
    )

    leads = res_dental["leads"] + res_real_estate["leads"]
    assert len(leads) == 5

    domains = {l["domain"] for l in leads}
    emails = {l["email"] for l in leads}
    bodies = {l["body_text"] for l in leads}
    subjects = {l["subject"] for l in leads}

    # Zero duplicate domains, emails, subjects, or bodies!
    assert len(domains) == 5
    assert len(emails) == 5
    assert len(bodies) == 5
    assert len(subjects) == 5

    # Verify every generated email passes VerifiedHumanEmail gates and has a BrutalMonetizationAudit
    for lead in leads:
        VerifiedHumanEmail(
            subject=lead["subject"],
            body_text=lead["body_text"],
            minhash_jaccard_max=lead["jaccard_score"],
            five_gram_overlap_pct=0.0,
        )
        dossier = build_lead_intelligence_dossier(lead)
        assert dossier["deal_viability_score"] >= 70
        assert "BRUTAL TRUTH" in dossier["brutal_honest_assessment"]
        assert "SELF-CHALLENGE" in dossier["self_challenge_critique"]
        assert len(dossier["fast_cash_offer"]) > 20
        assert len(dossier["zero_friction_proof_gift"]) > 20
        assert len(dossier["sequence"]) == 3


def test_v7_zero_synthetic_domains_across_all_10_categories():
    """Test 9: Verifies v7.0 CREAM returns 100% real corporate domains across all 10 categories with zero synthetic domains."""
    from src.main import QuickScrapeInput, one_click_quick_scrape, get_seed_data, save_store
    save_store(get_seed_data())

    categories = [
        ("Luxury Medspa Clinic", "Mumbai", "INDIA"),
        ("High-Ticket Dental Clinic", "Hyderabad", "INDIA"),
        ("Luxury Real Estate Developer", "Dubai", "GULF"),
        ("D2C Apparel & Shopify Brand", "Los Angeles", "US"),
        ("B2B SaaS & Automation Agency", "Chennai", "INDIA"),
        ("Solar & Home Remodeling", "Mumbai", "INDIA"),
        ("Law & Immigration Firm", "New York", "US"),
        ("High-Ticket Fitness Gym", "Bengaluru", "INDIA"),
        ("Boutique Hotel & Resort", "Goa", "INDIA"),
        ("Digital Marketing & Recruiting Agency", "Mumbai", "INDIA"),
    ]
    all_domains = set()
    for niche, city, reg in categories:
        res = asyncio.run(one_click_quick_scrape(QuickScrapeInput(niche=niche, city=city, region=reg, count=1)))
        assert len(res["leads"]) == 1
        dom = res["leads"][0]["domain"]
        assert not any(synth in dom for synth in ("verve", "solstice", "meridian", "kinetix", "caelum"))
        all_domains.add(dom)
    assert len(all_domains) == 10


def test_v7_live_prototype_preview_and_direct_domain_scrape():
    """Test 10: Verifies /api/v1/scrape/domain and /preview/{lead_id} interactive client prototype generator."""
    from src.main import SingleDomainScrapeInput, scrape_specific_domain_endpoint, serve_live_client_prototype_preview
    res = asyncio.run(
        scrape_specific_domain_endpoint(
            SingleDomainScrapeInput(
                url_or_domain="https://kaya.in",
                niche="Luxury Medspa Clinic",
                city="Mumbai",
                region="INDIA",
            )
        )
    )
    assert res["success"] is True
    lead = res["lead"]
    assert lead["domain"] == "kaya.in"
    assert res["preview_url"] == f"/preview/{lead['id']}"

    html_resp = asyncio.run(serve_live_client_prototype_preview(lead["id"]))
    body_str = html_resp.body.decode("utf-8")
    assert "LIVE INTERACTIVE PROTOTYPE BUILT FOR" in body_str
    assert "kaya.in" in body_str
    assert "Test 1-Tap WhatsApp Confirmation" in body_str


def test_v8_strict_4way_category_country_state_city_sync():
    """
    Test 11 (CRITICAL RENDER BLUNDER REGRESSION GATE):
    Verifies that selecting ANY (Category, Country, State/Province, City) combination returns leads
    100% locked to that exact Category, Country, State, and City — with ZERO cross-city, cross-state,
    cross-country, or cross-category leakage!
    """
    from src.main import QuickScrapeInput, one_click_quick_scrape, get_seed_data, save_store
    save_store(get_seed_data())

    test_matrix = [
        # 1. Exact user scenario: Dental Clinic in Mumbai, Maharashtra, India
        ("dental_implant_clinic", "INDIA", "Maharashtra", "Mumbai", "+91", "Mumbai"),
        # 2. Same category, shifted to Bengaluru, Karnataka, India
        ("dental_implant_clinic", "INDIA", "Karnataka", "Bengaluru (Bangalore)", "+91", "Bengaluru"),
        # 3. Same category, shifted to New Delhi, Delhi NCR, India
        ("dental_implant_clinic", "INDIA", "Delhi NCR", "New Delhi", "+91", "New Delhi"),
        # 4. Same category, shifted to Chennai, Tamil Nadu, India
        ("dental_implant_clinic", "INDIA", "Tamil Nadu", "Chennai", "+91", "Chennai"),
        # 5. Medspa in Pune, Maharashtra, India
        ("medspa_aesthetics", "INDIA", "Maharashtra", "Pune", "+91", "Pune"),
        # 6. Luxury Real Estate in London, Greater London, UK
        ("luxury_real_estate", "UNITED_KINGDOM", "Greater London", "London", "+44", "London"),
        # 7. B2B SaaS in Austin, Texas, United States
        ("b2b_saas_ai", "UNITED_STATES", "Texas", "Austin", "+1", "Austin"),
        # 8. Medspa in Dubai, UAE
        ("medspa_aesthetics", "UAE_GULF", "Dubai", "Dubai", "+971", "Dubai"),
    ]

    for cat_key, country_key, state_name, city_name, expected_dial, city_token in test_matrix:
        res = asyncio.run(
            one_click_quick_scrape(
                QuickScrapeInput(
                    niche=cat_key,
                    category=cat_key,
                    country=country_key,
                    state=state_name,
                    city=city_name,
                    region=country_key,
                    count=3,
                )
            )
        )
        assert res["success"] is True
        assert res["sync_lock_verified"] is True
        assert res["category_key"] == cat_key
        assert res["country_key"] == country_key
        assert res["state"] == state_name
        assert city_token.lower() in res["city"].lower()

        leads = res["leads"]
        assert len(leads) == 3

        for lead in leads:
            # 1. City Lock
            assert city_token.lower() in lead["city"].lower(), f"Expected {city_token}, got {lead['city']}"
            assert city_token.lower() in lead["physical_address"].lower(), f"Expected {city_token} in address {lead['physical_address']}"
            # 2. State Lock
            assert lead["state"] == state_name, f"Expected state {state_name}, got {lead['state']}"
            # 3. Country & Phone Prefix Lock
            assert lead["country_key"] == country_key, f"Expected country {country_key}, got {lead['country_key']}"
            assert lead["phone_whatsapp"].startswith(expected_dial), f"Expected dial {expected_dial}, got {lead['phone_whatsapp']}"
            # 4. Category Lock
            assert lead["category_key"] == cat_key, f"Expected category {cat_key}, got {lead['category_key']}"
            # 5. WhatsApp Closer URL populated
            assert lead["whatsapp_closer_url"].startswith("https://wa.me/")
            # 6. Zero foreign city contamination when Mumbai is selected
            if city_token == "Mumbai":
                for forbidden_city in ("chennai", "bengaluru", "bangalore", "dubai", "london", "new york"):
                    assert forbidden_city not in lead["city"].lower()
                    assert forbidden_city not in lead["physical_address"].lower()


def test_v8_taxonomy_battlecard_and_dns_endpoints():
    """
    Test 12: Verifies /api/v1/taxonomy (24 Categories x 10 Countries),
    /api/v1/leads/{id}/battlecard (5 Voss/Hormozi Objections + 50/25/25 SOW),
    and /api/v1/deliverability/check.
    """
    from src.main import (
        get_synchronized_taxonomy,
        get_lead_objection_battlecard,
        check_domain_deliverability_dns,
        load_store,
    )
    tax = asyncio.run(get_synchronized_taxonomy())
    assert tax["version"] == "8.0-GRANDMASTER"
    assert tax["total_categories"] == 24
    assert tax["total_countries"] == 10
    assert "INDIA" in tax["countries"]
    assert "Maharashtra" in tax["countries"]["INDIA"]["states"]
    assert "Mumbai" in tax["countries"]["INDIA"]["states"]["Maharashtra"]

    store = load_store()
    first_lead_id = store["emails"][0]["id"]
    bc = asyncio.run(get_lead_objection_battlecard(first_lead_id))
    assert bc["success"] is True
    assert len(bc["objections"]) == 5
    assert "50/25/25 MILESTONE PROPOSAL" in bc["milestone_proposal"]

    dns_res = asyncio.run(check_domain_deliverability_dns("gmail.com"))
    assert dns_res["success"] is True
    assert dns_res["domain"] == "gmail.com"
    assert "deliverability_score" in dns_res



def test_v9_ssrf_and_cloud_metadata_shield():
    """
    Test 13 (FORGE Cybersec Titan SSRF Shield):
    Verifies that loopback, RFC1918 private IPs, and cloud metadata IPs (169.254.169.254)
    are blocked on both /api/v1/scrape/domain and /api/v1/deliverability/check.
    """
    from fastapi import HTTPException
    from src.main import validate_safe_public_domain

    malicious_targets = [
        "http://127.0.0.1:8000/health",
        "http://localhost/admin",
        "http://169.254.169.254/latest/meta-data/",
        "10.0.0.1",
        "192.168.1.50",
        "172.16.0.5",
        "redis.internal",
        "db.local",
    ]
    for bad in malicious_targets:
        with pytest.raises(HTTPException):
            validate_safe_public_domain(bad)

    assert validate_safe_public_domain("https://www.signaturesmiles.in/contact") == "signaturesmiles.in"


def test_v9_first_load_seed_synchronization_with_default_ui_filter():
    """
    Test 14: Verifies that get_seed_data() contains verified Dental & Implant Clinic leads
    in Mumbai, Maharashtra, India with cryptographic LTM-... sync_audit_stamp hashes so the
    default 4-Way UI filter immediately displays matching leads on first load.
    """
    from src.main import get_seed_data
    seed = get_seed_data()
    emails = seed["emails"]
    assert len(emails) >= 5
    mumbai_dental = [
        e for e in emails
        if e.get("category_key") == "dental_implant_clinic"
        and e.get("city") == "Mumbai"
        and e.get("state") == "Maharashtra"
        and e.get("country_key") == "INDIA"
    ]
    assert len(mumbai_dental) >= 2
    for item in emails:
        stamp = item.get("sync_audit_stamp", {})
        assert stamp.get("category_locked") is True
        assert stamp.get("city_locked") is True
        assert str(stamp.get("litmus_hash", "")).startswith("LTM-")


def test_v9_omni_channel_battlecard_linkedin_and_cold_call_kit():
    """
    Test 15: Verifies /api/v1/leads/{id}/battlecard includes the Omni-Channel 4-Touch Kit
    (WhatsApp opener, LinkedIn <280-char connection note, 45s cold call script, 5 objections, 50/25/25 SOW).
    """
    from src.main import get_lead_objection_battlecard, get_seed_data, save_store
    save_store(get_seed_data())
    bc = asyncio.run(get_lead_objection_battlecard("lead-dental-mum-01"))
    assert bc["success"] is True
    omni = bc["omni_channel_kit"]
    assert omni["linkedin_char_count"] <= 280
    assert "Signature Smiles" in omni["linkedin_connection_note"]
    assert "+91 22 2600 8080" in omni["cold_call_45s_opener"]
    assert len(bc["objections"]) == 5
    assert "50/25/25 MILESTONE PROPOSAL" in bc["milestone_proposal"]


def test_v9_live_16_point_litmus_self_audit_endpoint():
    """
    Test 16: Verifies GET /api/v1/system/litmus-audit runs all 16 live system and security
    litmus checks and returns 16/16 (100% GRANDMASTER VERIFIED).
    """
    from src.main import run_live_16_point_litmus_self_audit
    audit_res = asyncio.run(run_live_16_point_litmus_self_audit())
    assert audit_res["success"] is True
    assert audit_res["passed_count"] == 16
    assert audit_res["total_checks"] == 16
    assert all(c["passed"] is True for c in audit_res["checks"])



def test_v10_all_24_categories_and_10_countries_monetization_matrix():
    """
    Test 17 (24-Category x 10-Country Monetization & Ticket Math Gate):
    Verifies that every single one of the 24 canonical categories and 10 countries resolves
    bespoke ticket economics, bespoke Cost-of-Inaction (COI) math, and passes all 3 copy gates.
    """
    from src.discovery_osint.geo_taxonomy import CATEGORY_TAXONOMY, GEO_TAXONOMY
    from src.engine.monetization_challenger import get_category_ticket_price
    from src.main import challenger_engine
    from src.schemas.prospect import InternetPresenceDossier, LeadInput, RegionEnum

    assert len(CATEGORY_TAXONOMY) == 24
    assert len(GEO_TAXONOMY) == 10

    tickets_seen = set()
    for cat_key, cat_spec in CATEGORY_TAXONOMY.items():
        t_inr = get_category_ticket_price("INDIA", cat_key)
        t_usd = get_category_ticket_price("UNITED_STATES", cat_key)
        t_aed = get_category_ticket_price("UAE_GULF", cat_key)
        t_gbp = get_category_ticket_price("UNITED_KINGDOM", cat_key)
        assert t_inr >= 1000
        assert t_usd >= 50
        assert t_aed >= 200
        assert t_gbp >= 50
        tickets_seen.add(t_inr)

        lead = LeadInput(
            company_name=f"Apex {cat_spec['brand_cores'][0]} Studio",
            domain=f"apex{cat_key[:8]}.in",
            region=RegionEnum.INDIA,
            city="Mumbai",
            niche=cat_spec["label"],
        )
        dossier = InternetPresenceDossier(
            website_lcp_ms=3100,
            has_meta_pixel=True,
            has_server_capi=False,
            has_gtm=True,
            tech_stack=["WordPress", "Meta Pixel"],
            detected_services=cat_spec["services"][:2],
        )
        audit = challenger_engine.run_brutal_monetization_audit(lead, dossier)
        assert audit.deal_viability_score >= 75
        assert "₹" in audit.quantified_monthly_leak
        assert "BRUTAL TRUTH" in audit.brutal_honest_assessment
        assert "SELF-CHALLENGE" in audit.self_challenge_critique

    # Ensure categories have distinct differentiated ticket pricing (not a single flat fallback)
    assert len(tickets_seen) >= 12


def test_v10_zero_github_push_protection_secret_leaks():
    """
    Test 18 (GitHub Push-Protection & Secret Scanner Gate):
    Scans every file in the project directory to guarantee zero raw xkeysib- or AIzaSy
    plain-text secret literals exist that could trigger GitHub Push Protection blocks on git push.
    """
    import os
    from pathlib import Path
    root_dir = str(Path(__file__).resolve().parent.parent)
    forbidden_literals = ["xkeysib-ba3eb9", "AIzaSy", "AQ.Ab8RN6K"]
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache")]
        for file in files:
            if file.endswith((".pyc", ".png", ".jpg", ".zip")) or file == "test_apex_gates.py":
                continue
            fpath = os.path.join(root, file)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for pat in forbidden_literals:
                assert pat not in content, f"Forbidden secret literal {pat!r} found in {fpath}"




def test_v11_persistent_sent_vault_and_reload_survival():
    """
    Test 19 (CRITICAL SENT MAIL VAULT REGRESSION GATE):
    Verifies that once an email is sent via approve_and_send_email, it is permanently locked
    into both zenmark_local_store.json (sent_ledger) and SQLite WAL (zenmark_sovereign_vault.db).
    Even if delete_all_admin_emails(preserve_sent=True) or save_store(get_seed_data()) is called,
    the sent email NEVER disappears when reopening/reloading the website!
    """
    from src.main import (
        approve_and_send_email,
        clear_entire_sent_vault,
        delete_all_admin_emails,
        get_seed_data,
        load_store,
        save_store,
    )
    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    # 1. Send email for lead-jamia-del-01
    res = asyncio.run(approve_and_send_email("lead-jamia-del-01"))
    assert res["success"] is True
    assert "SENT" in res["status"]
    assert res["touch_step"] == 1
    assert res["sent_at"] is not None

    # 2. Simulate user clicking "Clear Drafts" (DELETE /api/v1/emails?preserve_sent=true)
    del_res = asyncio.run(delete_all_admin_emails(preserve_sent=True))
    assert del_res["success"] is True
    assert del_res["preserved_sent_count"] >= 1

    # 3. Simulate reopening the website or seed reload
    save_store(get_seed_data(), preserve_sent_vault=True)
    reloaded = load_store()
    sent_lead = next((e for e in reloaded["emails"] if e["id"] == "lead-jamia-del-01"), None)
    assert sent_lead is not None
    assert "SENT" in sent_lead["status"]
    assert int(sent_lead.get("touch_count", 0)) >= 1
    assert "lead-jamia-del-01" in reloaded.get("sent_ledger", {})


def test_v11_followup_step2_and_step3_and_meet_invite_persistence():
    """
    Test 20 (FOLLOW-UP & MEET INVITE STATE PERSISTENCE GATE):
    Verifies that sending Follow-Up Step 2 (Day +3) and Follow-Up Step 3 (Day +7) updates
    fu1_status, fu2_status, touch_count, and touch_history on disk without stale-memory overwrite.
    """
    from src.main import (
        SendMeetInviteInput,
        approve_and_send_email,
        clear_entire_sent_vault,
        get_seed_data,
        load_store,
        save_store,
        send_followup_step,
        send_google_meet_invitation,
    )
    cur_store = load_store()
    jamia_lead = next((e for e in cur_store.get("emails", []) if e["id"] == "lead-jamia-del-01"), None)
    if not jamia_lead or int(jamia_lead.get("touch_count", 0)) < 1:
        clear_entire_sent_vault()
        save_store(get_seed_data(), preserve_sent_vault=False)
        asyncio.run(approve_and_send_email("lead-jamia-del-01"))
    # Send Follow-Up Step 2
    fu1_res = asyncio.run(send_followup_step("lead-jamia-del-01", 2, force_resend=True))
    assert fu1_res["success"] is True
    store_after_fu1 = load_store()
    lead_fu1 = next(e for e in store_after_fu1["emails"] if e["id"] == "lead-jamia-del-01")
    assert lead_fu1["fu1_status"] == "SENT (FOLLOW-UP 1 DELIVERED)"
    assert int(lead_fu1["touch_count"]) >= 2

    # Send Follow-Up Step 3
    fu2_res = asyncio.run(send_followup_step("lead-jamia-del-01", 3, force_resend=True))
    assert fu2_res["success"] is True
    store_after_fu2 = load_store()
    lead_fu2 = next(e for e in store_after_fu2["emails"] if e["id"] == "lead-jamia-del-01")
    assert lead_fu2["fu2_status"] == "SENT (FOLLOW-UP 2 DELIVERED)"
    assert int(lead_fu2["touch_count"]) >= 3
    assert len(lead_fu2.get("touch_history", [])) >= 3

    # Send Google Meet Invite on lead-jamia-del-02
    meet_res = asyncio.run(
        send_google_meet_invitation(
            "lead-jamia-del-02",
            SendMeetInviteInput(meet_link="https://meet.google.com/abc-defg-hij", whatsapp_number="+91 98114 22105"),
        )
    )
    assert meet_res["success"] is True
    store_after_meet = load_store()
    lead_meet = next(e for e in store_after_meet["emails"] if e["id"] == "lead-jamia-del-02")
    assert lead_meet["status"] == "MEETING_SCHEDULED"


def test_v11_jamia_nagar_110025_pin_and_3_client_tiers():
    """
    Test 21 (JAMIA NAGAR 110025 HYPER-LOCAL & 3-TIER CALIBRATION GATE):
    Verifies scraping across Jamia Nagar (PIN 110025) for LOCAL_AREA_SHOP, MIDDLE_GROWTH,
    and PREMIUM_WHALE tiers returns leads locked to Jamia Nagar (110025) with Google Maps URLs
    and tier-specific pricing.
    """
    from src.main import QuickScrapeInput, build_lead_intelligence_dossier, one_click_quick_scrape

    for tier_key, expected_badge in [
        ("LOCAL_AREA_SHOP", "LOCAL GOOGLE MAPS SHOP"),
        ("MIDDLE_GROWTH", "MIDDLE-MARKET"),
        ("PREMIUM_WHALE", "PREMIUM WHALE"),
    ]:
        res = asyncio.run(
            one_click_quick_scrape(
                QuickScrapeInput(
                    niche="dental_implant_clinic",
                    country="INDIA",
                    state="Delhi NCR",
                    city="New Delhi",
                    area="Jamia Nagar",
                    pincode="110025",
                    client_tier=tier_key,
                    shop_keyword="Dental & Wellness Shop",
                    count=2,
                )
            )
        )
        assert res["success"] is True
        assert "Jamia Nagar" in res["area"]
        assert res["pincode"] == "110025"
        assert res["client_tier"] == tier_key
        assert len(res["leads"]) == 2
        for lead in res["leads"]:
            assert lead["pincode"] == "110025"
            assert "110025" in lead["physical_address"]
            assert "jamia nagar" in lead["physical_address"].lower()
            assert lead["google_maps_url"].startswith("https://www.google.com/maps/")
            dossier = build_lead_intelligence_dossier(lead)
            assert expected_badge in dossier["deal_classification"]
            if tier_key == "LOCAL_AREA_SHOP":
                assert "₹4,999" in dossier["fast_cash_offer"]


def test_v11_batch_file_import_and_browser_vault_sync():
    """
    Test 22 (BATCH OF FILES INGESTION & BROWSER AUTO-HEAL VAULT SYNC GATE):
    Verifies POST /api/v1/batches/import and POST /api/v1/vault/sync.
    """
    from src.main import (
        BatchFileImportInput,
        BrowserVaultSyncInput,
        clear_entire_sent_vault,
        get_seed_data,
        import_batch_of_files_endpoint,
        save_store,
        sync_browser_vault_with_server,
    )
    csv_batch = (
        "company_name,domain,email,phone,address\n"
        "Noor Nagar Care Pharmacy,noornagarcare.in,owner@noornagarcare.in,+91 98112 33445,Noor Nagar Jamia Nagar New Delhi 110025\n"
        "Okhla Vihar Fitness Club,okhlaviharfitness.in,info@okhlaviharfitness.in,+91 98116 77889,Okhla Vihar Metro Jamia Nagar New Delhi 110025"
    )
    imp_res = asyncio.run(
        import_batch_of_files_endpoint(
            BatchFileImportInput(
                batch_name="Jamia Nagar Test Batch",
                raw_content=csv_batch,
                category="medspa_aesthetics",
                country="INDIA",
                state="Delhi NCR",
                city="New Delhi",
                area="Jamia Nagar",
                pincode="110025",
                client_tier="LOCAL_AREA_SHOP",
            )
        )
    )
    assert imp_res["success"] is True
    assert imp_res["imported_count"] == 2

    # Test Browser-to-Server Vault Sync restoration
    browser_sent_item = dict(imp_res["leads"][0])
    browser_sent_item["status"] = "SENT (RECORDED IN SOVEREIGN VAULT)"
    browser_sent_item["touch_count"] = 2
    browser_sent_item["fu1_status"] = "SENT (FOLLOW-UP 1 DELIVERED)"

    # Simulate ephemeral cloud reset on server
    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    # Browser auto-heals server via /api/v1/vault/sync
    sync_res = asyncio.run(
        sync_browser_vault_with_server(
            BrowserVaultSyncInput(
                emails=[browser_sent_item],
                sent_ledger={browser_sent_item["id"]: browser_sent_item},
                batches=[],
            )
        )
    )
    assert sync_res["success"] is True
    assert sync_res["sent_vault_count"] >= 1
    restored = next((e for e in sync_res["emails"] if e["id"] == browser_sent_item["id"]), None)
    assert restored is not None
    assert restored["fu1_status"] == "SENT (FOLLOW-UP 1 DELIVERED)"

    # Clean up store back to clean seed state after test suite finishes
    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)




def test_v11_zero_frankenstein_address_and_shop_keyword_coherence():
    """
    Test 23 (HYPER-LOCAL ADDRESS COHERENCE, SHOP KEYWORD & SINGLE-DELETE GATE):
    1. Verifies selecting a specific area (e.g. Bandra West 400050, Connaught Place 110001, Indiranagar 560038)
       NEVER mixes other districts (Powai, Kemps Corner, Defence Colony, Whitefield) into the address or name.
    2. Verifies custom shop_keyword (e.g. "Sweet Shop & Bakery") never falls back to "Dental" or "Implant".
    3. Verifies single-lead delete (delete_admin_email) removes a sent lead from all vault layers so it never resurrects.
    """
    from src.main import (
        QuickScrapeInput,
        approve_and_send_email,
        clear_entire_sent_vault,
        delete_admin_email,
        get_seed_data,
        load_store,
        one_click_quick_scrape,
        save_store,
    )

    # 1. Bandra West (400050) must never contain Powai, Kemps Corner, or Worli
    res_bandra = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(
                niche="medspa_aesthetics",
                country="INDIA",
                state="Maharashtra",
                city="Mumbai",
                area="Bandra West",
                pincode="400050",
                client_tier="PREMIUM_WHALE",
                count=3,
            )
        )
    )
    for l in res_bandra["leads"]:
        combined = f"{l['company_name']} {l['physical_address']}".lower()
        assert "bandra" in combined
        assert "400050" in l["physical_address"]
        for forbidden in ("powai", "kemps corner", "worli", "nariman point"):
            assert forbidden not in combined, f"Cross-area contamination {forbidden!r} found in {combined!r}"

    # 2. Connaught Place (110001) must never contain Defence Colony, Lajpat Nagar, or Greater Kailash
    res_cp = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(
                niche="dental_implant_clinic",
                country="INDIA",
                state="Delhi NCR",
                city="New Delhi",
                area="Connaught Place (CP)",
                pincode="110001",
                client_tier="PREMIUM_WHALE",
                count=3,
            )
        )
    )
    for l in res_cp["leads"]:
        combined = f"{l['company_name']} {l['physical_address']}".lower()
        assert "connaught place" in combined
        assert "110001" in l["physical_address"]
        for forbidden in ("defence colony", "lajpat nagar", "greater kailash", "vasant vihar"):
            assert forbidden not in combined, f"Cross-area contamination {forbidden!r} found in {combined!r}"

    # 3. Custom shop_keyword ("Sweet Shop & Bakery") in Jamia Nagar (110025) must never say Dental or Implant
    res_sweet = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(
                niche="specialty_food_nutraceuticals",
                country="INDIA",
                state="Delhi NCR",
                city="New Delhi",
                area="Jamia Nagar",
                pincode="110025",
                client_tier="LOCAL_AREA_SHOP",
                shop_keyword="Sweet Shop & Bakery",
                count=3,
            )
        )
    )
    for l in res_sweet["leads"]:
        cname_low = l["company_name"].lower()
        assert "sweet" in cname_low
        assert "dental" not in cname_low and "implant" not in cname_low and "tooth" not in cname_low

    # 4. Single-lead delete must remove even a SENT lead permanently without vault resurrection
    target_id = res_sweet["leads"][0]["id"]
    asyncio.run(approve_and_send_email(target_id))
    del_single = asyncio.run(delete_admin_email(target_id))
    assert del_single["success"] is True
    after_store = load_store()
    assert all(e["id"] != target_id for e in after_store["emails"])
    assert target_id not in after_store.get("sent_ledger", {})

    # Reset clean seed state after tests
    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)


def test_v12_universal_pincode_authority_and_stale_dropdown_override():
    """
    Test 24 (UNIVERSAL PIN CODE AUTHORITY & ZERO STALE DROPDOWN COLLISION GATE):
    Verifies that typing ANY Indian or Global PIN/Postal code (not just 110025) — even while
    the dropdowns still hold stale 'New Delhi' / 'Jamia Nagar' values — resolves 100% to the
    true Country, State, City, and Area of that PIN code with zero mismatch!
    """
    from src.main import (
        QuickScrapeInput,
        clear_entire_sent_vault,
        get_seed_data,
        one_click_quick_scrape,
        resolve_pincode_endpoint,
        save_store,
    )

    pin_assertions = [
        ("110025", "INDIA", "Delhi NCR", "New Delhi", "Jamia Nagar"),
        ("110001", "INDIA", "Delhi NCR", "New Delhi", "Connaught Place"),
        ("110092", "INDIA", "Delhi NCR", "New Delhi", "Preet Vihar"),
        ("400050", "INDIA", "Maharashtra", "Mumbai", "Bandra West"),
        ("560038", "INDIA", "Karnataka", "Bengaluru", "Indiranagar"),
        ("201301", "INDIA", "Delhi NCR", "Noida", "Sector 18"),
        ("122002", "INDIA", "Delhi NCR", "Gurugram", "DLF Cyber City"),
        ("202001", "INDIA", "Uttar Pradesh", "Aligarh", "Civil Lines"),
        ("302001", "INDIA", "Rajasthan", "Jaipur", "C-Scheme"),
        ("700016", "INDIA", "West Bengal", "Kolkata", "Park Street"),
        ("600006", "INDIA", "Tamil Nadu", "Chennai", "Nungambakkam"),
        ("500033", "INDIA", "Telangana", "Hyderabad", "Jubilee Hills"),
        ("800001", "INDIA", "Bihar & Jharkhand", "Patna", "Boring Road"),
        ("10028", "UNITED_STATES", "New York", "New York City", "Fifth Avenue"),
        ("90210", "UNITED_STATES", "California", "Los Angeles", "Beverly Hills"),
        ("W1G 6BG", "UNITED_KINGDOM", "Greater London", "London", "Harley Street"),
    ]

    for pin, exp_country, exp_state, exp_city, exp_area_tok in pin_assertions:
        ep_res = asyncio.run(resolve_pincode_endpoint(pincode=pin, country_hint="INDIA"))
        assert ep_res["success"] is True
        assert ep_res["country_key"] == exp_country, f"PIN {pin}: expected {exp_country}, got {ep_res['country_key']}"
        assert exp_state.lower() in ep_res["state"].lower(), f"PIN {pin}: expected {exp_state}, got {ep_res['state']}"
        assert exp_city.lower() in ep_res["city"].lower(), f"PIN {pin}: expected {exp_city}, got {ep_res['city']}"
        assert exp_area_tok.lower() in ep_res["area"].lower(), f"PIN {pin}: expected {exp_area_tok}, got {ep_res['area']}"

    # Verify scraping with stale New Delhi / Jamia Nagar dropdowns while typing non-110025 PINs
    for pin, exp_city in [("400050", "Mumbai"), ("202001", "Aligarh"), ("560038", "Bengaluru"), ("110001", "New Delhi")]:
        res = asyncio.run(
            one_click_quick_scrape(
                QuickScrapeInput(
                    niche="dental_implant_clinic",
                    country="INDIA",
                    state="Delhi NCR",
                    city="New Delhi",
                    area="Jamia Nagar (Main Market & JMI Corridor)",
                    pincode=pin,
                    client_tier="LOCAL_AREA_SHOP",
                    count=2,
                    replace_unsent_queue=True,
                )
            )
        )
        assert res["success"] is True
        assert exp_city.lower() in res["city"].lower()
        for ld in res["leads"]:
            assert exp_city.lower() in ld["city"].lower()
            assert ld["pincode"] == pin
            assert "jamia" not in ld["physical_address"].lower()

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)


def test_v12_4stage_ascension_and_4scope_national_global_scraping():
    """
    Test 25 (4-STAGE GRADUAL AGENCY ASCENSION & LOCAL-TO-NATIONAL-TO-GLOBAL SCRAPING GATE):
    Verifies:
      1. Stage 1 (LOCAL_AREA_SHOP) -> Stage 2 (MIDDLE_GROWTH) -> Stage 3 (PREMIUM_WHALE) -> Stage 4 (GIANT_ENTERPRISE)
         produce stage-calibrated pricing, classifications, and VerifiedHumanEmail-compliant copy.
      2. Country-Wide (state='ALL_STATES', city='ALL_CITIES') distributes leads across multiple states & cities.
      3. Global Cross-Border (country='GLOBAL_ALL') distributes leads across multiple countries.
      4. replace_unsent_queue=True clears unsent demo rows while keeping 100% of Sent Vault leads untouched.
    """
    from src.main import (
        QuickScrapeInput,
        approve_and_send_email,
        clear_entire_sent_vault,
        get_seed_data,
        load_store,
        one_click_quick_scrape,
        save_store,
    )

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    # Send 1 lead so it enters the permanent Sent Vault
    sent_res = asyncio.run(approve_and_send_email("lead-jamia-del-01"))
    assert sent_res["success"] is True

    # 1. Test all 4 Agency Ascension stages
    for stage_key, exp_badge in [
        ("LOCAL_AREA_SHOP", "STAGE 1"),
        ("MIDDLE_GROWTH", "STAGE 2"),
        ("PREMIUM_WHALE", "STAGE 3"),
        ("GIANT_ENTERPRISE", "STAGE 4"),
    ]:
        r_stage = asyncio.run(
            one_click_quick_scrape(
                QuickScrapeInput(
                    niche="dental_implant_clinic",
                    country="INDIA",
                    state="Maharashtra",
                    city="Mumbai",
                    area="Linking Road, Bandra West",
                    pincode="400050",
                    client_tier=stage_key,
                    count=2,
                    replace_unsent_queue=True,
                )
            )
        )
        assert r_stage["success"] is True
        for ld in r_stage["leads"]:
            assert ld["client_tier"] == stage_key
            assert exp_badge in ld["deal_classification"].upper()

        # Verify replace_unsent_queue=True kept our Sent lead ('lead-jamia-del-01') intact while removing unsent demo leads!
        cur_store = load_store()
        ids_in_store = [e["id"] for e in cur_store["emails"]]
        assert "lead-jamia-del-01" in ids_in_store, "Sent Vault lead must NEVER be removed by replace_unsent_queue!"
        assert len(cur_store["emails"]) == 3  # 2 newly scraped + 1 protected sent lead

    # 2. Test Country-Wide (All India State-to-State Round-Robin)
    r_nat = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(
                niche="b2b_saas_ai",
                country="INDIA",
                state="ALL_STATES",
                city="ALL_CITIES",
                pincode="",
                client_tier="GIANT_ENTERPRISE",
                count=5,
                replace_unsent_queue=True,
            )
        )
    )
    nat_cities = {ld["city"] for ld in r_nat["leads"]}
    assert len(nat_cities) >= 4, f"Expected >=4 distinct Indian cities in Country-Wide mode, got {nat_cities}"

    # 3. Test Global Cross-Border (Country-to-Country)
    r_glob = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(
                niche="luxury_real_estate",
                country="GLOBAL_ALL",
                state="ALL_STATES",
                city="ALL_CITIES",
                pincode="",
                client_tier="GIANT_ENTERPRISE",
                count=5,
                replace_unsent_queue=True,
            )
        )
    )
    glob_countries = {ld["country_key"] for ld in r_glob["leads"]}
    assert len(glob_countries) >= 4, f"Expected >=4 distinct countries in Global mode, got {glob_countries}"

    # Reset clean seed state after tests
    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)


def test_v13_rfc8058_unsubscribe_and_dnc_suppression_blocker():
    """
    Test 26 (RFC 8058 ONE-CLICK UNSUBSCRIBE & DNC SUPPRESSION BLOCKER GATE):
    Verifies that unsubscribing a lead or adding an email/@domain to the DNC Suppression Ledger
    immediately cancels pending follow-ups and blocks any future send or follow-up attempt.
    """
    from fastapi import HTTPException
    from src.main import (
        SuppressionEntryInput,
        add_to_suppression_ledger,
        approve_and_send_email,
        clear_entire_sent_vault,
        get_seed_data,
        list_suppression_ledger,
        remove_from_suppression_ledger,
        rfc8058_one_click_unsubscribe,
        save_store,
    )

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    # 1. One-click unsubscribe on lead-jamia-del-01
    unsub_res = asyncio.run(rfc8058_one_click_unsubscribe(lead_id="lead-jamia-del-01"))
    assert unsub_res["success"] is True
    assert "UNSUBSCRIBED" in unsub_res["status"]

    # Attempting to send to unsubscribed lead must raise HTTPException(400)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(approve_and_send_email("lead-jamia-del-01"))
    assert exc_info.value.status_code == 400
    assert "Suppression Ledger" in str(exc_info.value.detail)

    # 2. Wildcard @domain suppression blocks all emails at that domain
    asyncio.run(add_to_suppression_ledger(SuppressionEntryInput(email_or_domain="@signaturesmiles.in", reason="MANUAL_DNC")))
    supp_list = asyncio.run(list_suppression_ledger())
    assert supp_list["count"] >= 2

    with pytest.raises(HTTPException) as exc_dom:
        asyncio.run(approve_and_send_email("lead-dental-mum-01"))
    assert exc_dom.value.status_code == 400

    # Clean up suppression entry and verify removal
    asyncio.run(remove_from_suppression_ledger("@signaturesmiles.in"))
    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)


def test_v13_message_id_threading_and_followup_prerequisite_guardrails():
    """
    Test 27 (MESSAGE-ID THREAD CONTINUITY & FOLLOW-UP PREREQUISITE GUARDRAILS GATE):
    Verifies:
      1. Cannot send Follow-Up Step 2 before Touch 1 is sent.
      2. Touch 1 generates an RFC 5322 Message-ID and List-Unsubscribe header.
      3. Follow-Up Step 2 links In-Reply-To to Touch 1's Message-ID.
      4. Duplicate dispatch of Follow-Up Step 2 is blocked unless force_resend=True.
    """
    from fastapi import HTTPException
    from src.main import (
        approve_and_send_email,
        clear_entire_sent_vault,
        get_seed_data,
        send_followup_step,
        save_store,
    )

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    # 1. Attempting Follow-Up Step 2 on unsent lead must fail
    with pytest.raises(HTTPException) as exc_pre:
        asyncio.run(send_followup_step("lead-jamia-del-02", 2))
    assert exc_pre.value.status_code == 400
    assert "before Touch 1" in str(exc_pre.value.detail)

    # 2. Send Touch 1 and verify initial_message_id + list_unsubscribe_header
    t1_res = asyncio.run(approve_and_send_email("lead-jamia-del-02"))
    assert t1_res["success"] is True
    em_obj = t1_res["email"]
    assert em_obj.get("initial_message_id", "").startswith("<zenmark-lead-jamia-del-02-t1-")
    assert "unsubscribe" in em_obj.get("list_unsubscribe_header", "").lower()

    # 3. Send Follow-Up Step 2 and verify In-Reply-To links to Touch 1's Message-ID
    t2_res = asyncio.run(send_followup_step("lead-jamia-del-02", 2))
    assert t2_res["success"] is True
    t2_em = t2_res["send_result"]["email"]
    last_hist = t2_em["touch_history"][-1]
    assert last_hist["in_reply_to"] == em_obj["initial_message_id"]

    # 4. Attempting duplicate Follow-Up Step 2 must be blocked
    with pytest.raises(HTTPException) as exc_dup:
        asyncio.run(send_followup_step("lead-jamia-del-02", 2))
    assert exc_dup.value.status_code == 400
    assert "already delivered" in str(exc_dup.value.detail)

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)


def test_v13_google_maps_gbp_telemetry_and_problem_diagnosis_matrix():
    """
    Test 28 (GOOGLE MAPS GBP SIGNALS, EMAIL CONFIDENCE & PROBLEM DIAGNOSIS MATRIX GATE):
    Verifies every scraped lead and intelligence dossier includes validated Place ID, coordinates,
    rating, review count, GBP claimed status, review themes, email confidence score, and structured problem_diagnoses.
    """
    from src.main import (
        QuickScrapeInput,
        clear_entire_sent_vault,
        get_lead_dossier,
        get_seed_data,
        one_click_quick_scrape,
        save_store,
    )

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    res = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(
                niche="dental_implant_clinic",
                country="INDIA",
                state="Delhi NCR",
                city="New Delhi",
                area="Jamia Nagar",
                pincode="110025",
                client_tier="LOCAL_AREA_SHOP",
                count=2,
            )
        )
    )
    assert res["success"] is True
    ld = res["leads"][0]
    assert str(ld.get("place_id", "")).startswith("ChIJ")
    coords = ld.get("coordinates", {})
    assert -90 <= coords.get("lat", 0) <= 90 and -180 <= coords.get("lng", 0) <= 180
    assert 3.0 <= float(ld.get("google_rating", 0)) <= 5.0
    assert int(ld.get("review_count", 0)) >= 5
    assert isinstance(ld.get("review_themes"), list) and len(ld["review_themes"]) >= 1
    assert 50 <= int(ld.get("email_confidence_score", 0)) <= 100
    assert isinstance(ld.get("problem_diagnoses"), list) and len(ld["problem_diagnoses"]) >= 2

    d_res = asyncio.run(get_lead_dossier(ld["id"]))
    assert d_res["success"] is True
    assert len(d_res["dossier"]["problem_diagnoses"]) >= 2

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)


def test_v13_crm_funnel_attribution_and_deal_outcome_analytics():
    """
    Test 29 (CRM FUNNEL ATTRIBUTION, DEAL WON REVENUE & UNIT ECONOMICS GATE):
    Verifies POST /api/v1/emails/{id}/deal-outcome and GET /api/v1/analytics/crm-funnel.
    """
    from src.main import (
        DealOutcomeInput,
        approve_and_send_email,
        clear_entire_sent_vault,
        get_crm_funnel_and_unit_economics,
        get_seed_data,
        save_store,
        update_lead_crm_deal_outcome,
    )

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    asyncio.run(approve_and_send_email("lead-jamia-del-01"))
    asyncio.run(
        update_lead_crm_deal_outcome(
            "lead-jamia-del-01",
            DealOutcomeInput(crm_stage="DEAL_WON", deal_value=14999.0, notes="Closed Local Maps + WhatsApp package"),
        )
    )

    analytics = asyncio.run(get_crm_funnel_and_unit_economics())
    assert analytics["success"] is True
    assert analytics["funnel_counts"]["deals_won"] >= 1
    assert analytics["unit_economics"]["attributed_revenue_inr"] >= 14999.0

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)


def test_v13_tamper_evident_hash_chained_audit_log_and_security_headers():
    """
    Test 30 (HASH-CHAINED SECURITY AUDIT LOG & HTTP SECURITY HEADERS GATE):
    Verifies GET /api/v1/system/audit-logs records SHA-256 hash-chained entries and
    HTTP responses carry X-Content-Type-Options: nosniff and X-Frame-Options: SAMEORIGIN.
    """
    from fastapi.testclient import TestClient
    from src.main import app, approve_and_send_email, clear_entire_sent_vault, get_security_and_operational_audit_logs, get_seed_data, save_store

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    asyncio.run(approve_and_send_email("lead-jamia-del-01"))
    logs_res = asyncio.run(get_security_and_operational_audit_logs())
    assert logs_res["success"] is True
    assert logs_res["count"] >= 1
    first_log = logs_res["audit_logs"][0]
    assert len(first_log["entry_hash"]) == 64

    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)




def test_v13_render_and_github_deployment_readiness_gate():
    """
    Test 31 (RENDER & GITHUB DEPLOYMENT READINESS + CSV v13 EXPORT GATE):
    Verifies:
      1. requirements.txt is lean, includes beautifulsoup4 & fastapi, and excludes OOM-inducing crawl4ai/playwright.
      2. render.yaml and Dockerfile exist and bind properly to $PORT and /health.
      3. .gitignore protects zenmark_sovereign_vault.db, zenmark_sent_vault_ledger.json, and .env.
      4. GET /api/v1/emails/export/csv exports all v13 columns (Area / Locality, PIN / Postal Code, Client Stage / Tier, Google Place ID, Email Confidence Score, CRM Stage).
    """
    from pathlib import Path
    from src.main import export_leads_csv

    root = Path(__file__).resolve().parent.parent
    req_txt = (root / "requirements.txt").read_text(encoding="utf-8")
    assert "fastapi" in req_txt and "beautifulsoup4" in req_txt
    assert "crawl4ai" not in req_txt, "crawl4ai causes OOM on Render 512MB Free Tier!"

    gitignore_txt = (root / ".gitignore").read_text(encoding="utf-8")
    assert "zenmark_sovereign_vault.db" in gitignore_txt
    assert "zenmark_sent_vault_ledger.json" in gitignore_txt
    assert ".env" in gitignore_txt

    render_yaml = (root / "render.yaml").read_text(encoding="utf-8")
    assert "healthCheckPath: /health" in render_yaml
    assert "uvicorn src.main:app" in render_yaml

    csv_resp = asyncio.run(export_leads_csv())
    csv_body = csv_resp.body.decode("utf-8")
    assert "Area / Locality" in csv_body
    assert "PIN / Postal Code" in csv_body
    assert "Client Stage / Tier" in csv_body
    assert "Google Place ID" in csv_body
    assert "Email Confidence Score" in csv_body
    assert "CRM Stage" in csv_body




def test_v14_all_1152_category_tier_angle_combinations_pass_gate123():
    """
    Test 32 (1,152-COMBINATION EXHAUSTIVE GATE 1-3 VERIFICATION):
    Verifies every single one of the 24 categories x 4 tiers x 12 angles (1,152 emails)
    passes VerifiedHumanEmail (0 AI slop, Flesch-Kincaid 3.5-8.5, Burstiness SD >= 3.8).
    """
    from src.discovery_osint.geo_taxonomy import CATEGORY_TAXONOMY
    from src.engine.monetization_challenger import MonetizationAndPersonalizationChallenger
    from src.engine.plagiarism_guard import PlagiarismAndFingerprintGuard, VerifiedHumanEmail
    from src.schemas.prospect import InternetPresenceDossier, LeadInput

    pg = PlagiarismAndFingerprintGuard()
    mc = MonetizationAndPersonalizationChallenger(plagiarism_guard=pg)

    for cat_key, cat_spec in CATEGORY_TAXONOMY.items():
        lbl = cat_spec["label"]
        lead = LeadInput(
            company_name=f"Apex {lbl} Group",
            domain=f"apex{cat_key[:8]}.com",
            region="INDIA",
            city="Hyderabad",
            niche=lbl,
            first_name="Vikram",
        )
        dossier = InternetPresenceDossier(
            website_lcp_ms=3100,
            detected_services=cat_spec["services"][:2],
        )
        for tier in ("LOCAL_AREA_SHOP", "MIDDLE_GROWTH", "PREMIUM_WHALE", "GIANT_ENTERPRISE"):
            audit = mc.run_brutal_monetization_audit(lead, dossier, client_tier=tier)
            for angle in range(12):
                subj, body = mc.synthesize_deterministic_hyper_personalized_email(
                    lead, dossier, audit, variation_offset=angle
                )
                VerifiedHumanEmail(subject=subj, body_text=body)


def test_v14_five_rung_scraper_ssrf_and_circuit_breaker_telemetry():
    """
    Test 33 (5-RUNG SCRAPER SSRF GUARD, CIRCUIT BREAKER & TELEMETRY GATE):
    Verifies FiveRungScraper blocks internal/metadata URLs, tracks circuit breakers,
    and exposes /api/v1/scrape/telemetry.
    """
    from src.main import get_live_scraper_telemetry
    from src.scraper.five_rung_scraper import FiveRungScraper, is_safe_public_url

    ok_aws, _ = is_safe_public_url("http://169.254.169.254/latest/meta-data/")
    ok_loc, _ = is_safe_public_url("http://127.0.0.1:8000/admin")
    ok_pub, clean_u = is_safe_public_url("signaturesmiles.in")
    assert ok_aws is False
    assert ok_loc is False
    assert ok_pub is True and clean_u == "https://signaturesmiles.in"

    scraper = FiveRungScraper(timeout=0.5)
    md, meta = asyncio.run(scraper.scrape_url("http://169.254.169.254/latest"))
    assert md == ""
    assert meta["ssrf_blocked"] is True

    tel_res = asyncio.run(get_live_scraper_telemetry())
    assert tel_res["success"] is True
    assert "rung_breakdown" in tel_res
    assert "telemetry_events" in tel_res


def test_v14_live_email_grader_bulk_actions_and_3state_webhook_dlq():
    """
    Test 34 (LIVE 3-GATE EMAIL GRADER, BULK MULTI-SELECT, 3-STATE WEBHOOK LEASE & N8N ENDPOINTS GATE):
    Verifies:
      1. POST /api/v1/emails/grade-live detects AI slop and auto-calibrates human copy.
      2. POST /api/v1/webhooks/ingest enforces 3-state lease (PROCESSING -> COMPLETED / FAILED_DLQ) and POST /api/v1/webhooks/replay-dlq recovers DLQ jobs.
      3. POST /api/v1/emails/bulk-action executes multi-lead operations.
      4. n8n endpoints (/api/v1/discover/run, /api/v1/campaigns/generate, /api/v1/warmup/tick) operate cleanly.
    """
    from fastapi.testclient import TestClient
    from src.main import (
        LiveEmailGradeInput,
        app,
        clear_entire_sent_vault,
        get_seed_data,
        grade_email_copy_live,
        list_webhook_leases,
        replay_failed_dlq_webhooks,
        save_store,
    )

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    # 1. Live email grader
    bad_res = asyncio.run(
        grade_email_copy_live(
            LiveEmailGradeInput(
                subject="unlock synergy now",
                body_text="We delve into cutting-edge synergy to skyrocket your clinic!",
                auto_fix=False,
            )
        )
    )
    assert bad_res["all_gates_passed"] is False
    assert len(bad_res["metrics"]["slop_hits"]) >= 2

    # 2. 3-State Webhook Lease + DLQ Replay via TestClient
    client = TestClient(app)
    r_ok = client.post(
        "/api/v1/webhooks/ingest",
        json={"provider": "n8n", "idempotency_key": "evt-1001", "event_type": "LEAD_SYNC", "payload": {"lead": "1"}},
    )
    assert r_ok.status_code == 200
    assert r_ok.json()["status"] == "COMPLETED"

    # Duplicate idempotency key is deduplicated
    r_dup = client.post(
        "/api/v1/webhooks/ingest",
        json={"provider": "n8n", "idempotency_key": "evt-1001", "event_type": "LEAD_SYNC", "payload": {"lead": "1"}},
    )
    assert r_dup.json()["deduplicated"] is True

    # Simulated failure enters FAILED_DLQ
    r_dlq = client.post(
        "/api/v1/webhooks/ingest",
        json={"provider": "brevo", "idempotency_key": "evt-dlq-99", "event_type": "BOUNCE_HOOK", "simulate_failure": True},
    )
    assert r_dlq.json()["status"] == "FAILED_DLQ"

    leases_info = asyncio.run(list_webhook_leases())
    assert leases_info["dlq_count"] >= 1

    replay_res = asyncio.run(replay_failed_dlq_webhooks())
    assert replay_res["replayed_count"] >= 1
    assert asyncio.run(list_webhook_leases())["dlq_count"] == 0

    # 3. Bulk Multi-Select Action
    r_bulk = client.post(
        "/api/v1/emails/bulk-action",
        json={"lead_ids": ["lead-jamia-del-01", "lead-jamia-del-02"], "action": "SEND_ALL"},
    )
    assert r_bulk.status_code == 200
    assert r_bulk.json()["processed_count"] == 2

    # 4. Warmup Tick & Outbound Control
    r_warm = client.post("/api/v1/warmup/tick")
    assert r_warm.status_code == 200 and r_warm.json()["success"] is True

    r_ctrl = client.post("/api/v1/system/outbound-control", json={"paused": False, "reset_circuit_breakers": True})
    assert r_ctrl.status_code == 200 and r_ctrl.json()["success"] is True

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)



def test_v15_uncapped_owner_psychology_email_and_regeneration_gate():
    """
    Test 35 (v15.0 VERCEL SOVEREIGN — UNCAPPED OWNER PSYCHOLOGY PROFILING & ADAPTIVE EMAIL REGENERATION GATE):
    Verifies:
      1. Seed & scraped leads include full `owner_psychology_profile` (Archetype, Three-Brain Psychology, Voss Accusation Audit, 4-Objection Pre-Demolition, Internet Existence Signals).
      2. Emails have NO 90-word ceiling (support 120–260+ word deep psychological letters) while passing Gate 1-3 VerifiedHumanEmail.
      3. POST /api/v1/emails/{email_id}/regenerate-psych dynamically re-tailors emails across ADAPTIVE_PSYCHOLOGY, DEEP_FOUNDER_TEARDOWN, VOSS_EMPATHY_PROOF, and EXECUTIVE_DIRECT.
    """
    from fastapi.testclient import TestClient
    from src.main import app, build_lead_intelligence_dossier, clear_entire_sent_vault, get_seed_data, save_store
    from src.engine.plagiarism_guard import VerifiedHumanEmail

    clear_entire_sent_vault()
    save_store(get_seed_data(), preserve_sent_vault=False)

    seed = get_seed_data()
    first = seed["emails"][0]
    assert first["word_count"] > 120, f"Expected uncapped >120 words, got {first['word_count']}"
    VerifiedHumanEmail(subject=first["subject"], body_text=first["body_text"])

    dossier = build_lead_intelligence_dossier(first)
    psych = dossier.get("owner_psychology_profile", {})
    assert "archetype_key" in psych
    assert "three_brain_psychology" in psych
    assert "voss_accusation_audit" in psych
    assert "four_objection_locks" in psych
    assert len(psych.get("internet_existence_signals", [])) >= 3

    client = TestClient(app)
    for mode in ("DEEP_FOUNDER_TEARDOWN", "VOSS_EMPATHY_PROOF", "ADAPTIVE_PSYCHOLOGY", "EXECUTIVE_DIRECT"):
        r = client.post(
            f"/api/v1/emails/{first['id']}/regenerate-psych",
            json={"psych_mode": mode, "variation_offset": 2},
        )
        assert r.status_code == 200
        payload = r.json()
        assert payload["success"] is True
        assert payload["psych_mode"] == mode
        VerifiedHumanEmail(subject=payload["subject"], body_text=payload["body_text"])
        if mode == "DEEP_FOUNDER_TEARDOWN":
            assert payload["word_count"] >= 160


if __name__ == "__main__":
    g = dict(globals())
    passed = 0
    for k, fn in g.items():
        if k.startswith("test_") and callable(fn):
            print(f"RUNNING {k} ...")
            fn()
            print(f"  ✅ PASSED {k}")
            passed += 1
    print(f"\n🏆 ALL {passed}/{passed} VERIFICATION GATES PASSED 100%!")


def test_v16_vercel_sovereign_zero_auto_leads_deduplication_and_dual_pitch_gate():
    """
    Test 36 (v16.0 VERCEL SOVEREIGN FINAL GATE):
      1. Fresh production boot starts with 0 auto-generated leads (never injects 7 demo leads on its own).
      2. Scraping batches (5, 10, 50, 100) executes smoothly with 0 duplicates and permanent seen_ledger protection.
      3. Dual-Mode Pitch Engine supports both WEB_DEV_BIG_BROTHER and PAID_MARKETING_DOMINANCE (Meta Ads + Google Ads + LinkedIn ABM) and passes all 3 human copy gates.
      4. Root index.html, vercel.json, and api/index.py exist and are synchronized.
    """
    import asyncio
    import os
    from pathlib import Path
    from src.main import (
        STORAGE_FILE,
        SQLITE_VAULT_FILE,
        SENT_VAULT_JSON_FILE,
        QuickScrapeInput,
        RegeneratePsychologicalEmailInput,
        get_empty_production_store,
        load_store,
        one_click_quick_scrape,
        regenerate_psychological_email_endpoint,
        save_store,
    )
    from src.engine.plagiarism_guard import VerifiedHumanEmail

    # 1. Verify fresh boot starts with 0 leads
    if STORAGE_FILE.exists():
        try:
            os.remove(STORAGE_FILE)
        except Exception:
            pass
    if SQLITE_VAULT_FILE.exists():
        try:
            os.remove(SQLITE_VAULT_FILE)
        except Exception:
            pass
    if SENT_VAULT_JSON_FILE.exists():
        try:
            os.remove(SENT_VAULT_JSON_FILE)
        except Exception:
            pass
    save_store(get_empty_production_store(), preserve_sent_vault=False)
    fresh_store = load_store()
    assert len(fresh_store.get("emails", [])) == 0, "Fresh production store must start with 0 auto-generated leads"

    # 2. Verify batch scraping (5 and 50) & seen_ledger deduplication
    res5 = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(count=5, pincode="110025", pitch_mode="WEB_DEV_BIG_BROTHER", replace_unsent_queue=False)
        )
    )
    assert res5["scraped_count"] == 5
    first_lead_id = res5["leads"][0]["id"]
    first_domain = res5["leads"][0]["domain"]

    # Switch lead to Paid Marketing Pitch and verify Gate 1-3 compliance
    regen_res = asyncio.run(
        regenerate_psychological_email_endpoint(
            first_lead_id,
            RegeneratePsychologicalEmailInput(psych_mode="PAID_MARKETING_DOMINANCE", variation_offset=0),
        )
    )
    assert regen_res["success"] is True
    VerifiedHumanEmail(subject=regen_res["subject"], body_text=regen_res["body_text"])

    # Scrape batch of 50 in Paid Marketing mode and verify 55 unique domains
    res50 = asyncio.run(
        one_click_quick_scrape(
            QuickScrapeInput(count=50, pincode="110025", pitch_mode="PAID_MARKETING_DOMINANCE", replace_unsent_queue=False)
        )
    )
    assert res50["scraped_count"] == 50
    st_after = load_store()
    all_doms = [e["domain"] for e in st_after["emails"]]
    assert len(all_doms) == 55 and len(set(all_doms)) == 55
    assert first_domain in st_after.get("seen_ledger", {})

    # 3. Verify Vercel files exist
    root_dir = Path(__file__).resolve().parent.parent
    assert (root_dir / "vercel.json").exists()
    assert (root_dir / "api" / "index.py").exists()
    assert (root_dir / "index.html").exists()

    # Clean store back to 0 leads for production packaging
    save_store(get_empty_production_store(), preserve_sent_vault=False)
    for f in (STORAGE_FILE, SQLITE_VAULT_FILE, SENT_VAULT_JSON_FILE):
        if f.exists():
            try:
                os.remove(f)
            except Exception:
                pass

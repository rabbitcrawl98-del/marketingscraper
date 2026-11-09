from __future__ import annotations
from typing import Dict, List
from src.engine.plagiarism_guard import VerifiedHumanEmail

GOLDEN_EMAIL_BANK: List[Dict[str, str]] = [
    # 1. US - Track A (Meta Ads + CRO Funnel)
    {
        "id": "US_TRACK_A_META_ADS",
        "region": "US",
        "track": "TRACK_A_META_ADS",
        "subject": "meta ad traffic on your site",
        "body_text": (
            "Looked at your active ads.\n"
            "Your six video ads have good hooks, but they send phone traffic straight to your slow homepage with no server tracking.\n"
            "You lose about thirty percent of paid buyers before pixels load.\n"
            "We made a quick mobile preview showing your exact store with fast checkout.\n"
            "Are you completely against looking at the preview link?"
        ),
    },
    # 2. US - Track B (Full-Stack Dev / Automation)
    {
        "id": "US_TRACK_B_DEV_AUTOMATION",
        "region": "US",
        "track": "TRACK_B_DEV_AUTOMATION",
        "subject": "booking delays on your site",
        "body_text": (
            "Read your recent client reviews.\n"
            "Several buyers noted that your team took twelve hours to confirm their booking requests on busy weekdays.\n"
            "Your website has no instant text confirmation, so qualified calls slip to other clinics nearby.\n"
            "We built a short workflow connecting your forms to instant calendar scheduling.\n"
            "Are you open to seeing how this recaptures lost calls?"
        ),
    },
    # 3. US - Track C (Dual Stack / Omnichannel)
    {
        "id": "US_TRACK_C_DUAL_STACK",
        "region": "US",
        "track": "TRACK_C_DUAL_STACK",
        "subject": "checkout speed on your store",
        "body_text": (
            "Tested your mobile store yesterday.\n"
            "Your team runs twelve ads on Instagram, yet your product page takes four seconds to show up on phones.\n"
            "You lose eager buyers who leave before product pictures finish loading.\n"
            "We made a fast clean shop page matching your current brand style.\n"
            "Are you against looking over the short preview link?"
        ),
    },
    # 4. EU - Track A (GDPR CAPI + Paid Meta)
    {
        "id": "EU_TRACK_A_META_ADS",
        "region": "EU",
        "track": "TRACK_A_META_ADS",
        "subject": "server tracking on your store",
        "body_text": (
            "Checked your store tracking.\n"
            "Your team runs solid paid Meta ads in Britain, but your checkout drops click tags on mobile Safari.\n"
            "You lose clear sales numbers under strict privacy rules without a first-party server connection.\n"
            "We made a clean server script that fixes lost tags.\n"
            "Are you completely against reviewing the short breakdown?"
        ),
    },
    # 5. EU - Track B (Custom Web / B2B SaaS)
    {
        "id": "EU_TRACK_B_DEV_AUTOMATION",
        "region": "EU",
        "track": "TRACK_B_DEV_AUTOMATION",
        "subject": "client intake on your portal",
        "body_text": (
            "Tested your client sign up page.\n"
            "Your firm offers great work, but your intake form needs manual review before buyers get their login.\n"
            "Your buyers wait hours for a reply while competitors give fast access.\n"
            "We sketched a fast intake tool that checks client files right away.\n"
            "Are you against taking a quick look at the plan?"
        ),
    },
    # 6. GULF - Track A (Meta / CTWA + Luxury Speed)
    {
        "id": "GULF_TRACK_A_META_ADS",
        "region": "GULF",
        "track": "TRACK_A_META_ADS",
        "subject": "whatsapp lead routing in dubai",
        "body_text": (
            "Saw your new clinic promotions.\n"
            "Your Instagram ads attract high interest in Dubai, but your contact link routes buyers to a slow web form.\n"
            "You miss urgent bookings because local clients expect instant WhatsApp chat within minutes of clicking.\n"
            "We drafted a quick chat booking setup matching your brand tone.\n"
            "Are you against reviewing the short preview link?"
        ),
    },
    # 7. GULF - Track B (Real Estate / High-Ticket Ops)
    {
        "id": "GULF_TRACK_B_DEV_AUTOMATION",
        "region": "GULF",
        "track": "TRACK_B_DEV_AUTOMATION",
        "subject": "property lead sync in riyadh",
        "body_text": (
            "Reviewed your villa listings.\n"
            "Your campaigns get high-value buyer calls, but your sales staff shares lead contacts on sheets by hand.\n"
            "You lose deals when overseas buyers wait half a day for price lists.\n"
            "We set up a direct tool sending new buyers straight to agent phones.\n"
            "Are you completely against seeing how this speeds up buyer replies?"
        ),
    },
    # 8. GULF - Track C (3D Web + Concierge Closer)
    {
        "id": "GULF_TRACK_C_DUAL_STACK",
        "region": "GULF",
        "track": "TRACK_C_DUAL_STACK",
        "subject": "mobile catalog speed for buyers",
        "body_text": (
            "Looked at your watch gallery.\n"
            "Your brand sells rare pieces, but your mobile page takes five seconds to show all photos.\n"
            "You risk losing top buyers who want fast mobile browsing on their phones.\n"
            "We built a smooth light gallery showing your pieces with fast video view.\n"
            "Are you against taking a quick look at the preview?"
        ),
    },
    # 9. INDIA - Track A (COD RTO Reduction + Meta CRO)
    {
        "id": "INDIA_TRACK_A_META_ADS",
        "region": "INDIA",
        "track": "TRACK_A_META_ADS",
        "subject": "rto leakage on your store",
        "body_text": (
            "Looked at your shoe store.\n"
            "Your brand drives great sales on Meta ads, but your cart takes cash orders without quick text confirmation.\n"
            "You lose good margin because buyers cancel orders before delivery teams reach them.\n"
            "We built a quick WhatsApp check flow offering UPI discounts that cut return rates.\n"
            "Are you against looking over the quick flow chart?"
        ),
    },
    # 10. INDIA - Track B (Clinic / B2B Lead Engine)
    {
        "id": "INDIA_TRACK_B_DEV_AUTOMATION",
        "region": "INDIA",
        "track": "TRACK_B_DEV_AUTOMATION",
        "subject": "patient booking speed in mumbai",
        "body_text": (
            "Found your clinic on Google.\n"
            "Your doctors have great patient ratings, but your visit form asks people to wait for a phone callback.\n"
            "You lose patients to other clinics when visits cannot be booked right away on WhatsApp.\n"
            "We made a simple booking widget that places patient slots right on your calendar.\n"
            "Are you completely against looking at the quick preview?"
        ),
    },
    # 11. PAKISTAN - Track A (Export D2C + Meta Scale)
    {
        "id": "PAKISTAN_TRACK_A_META_ADS",
        "region": "PAKISTAN",
        "track": "TRACK_A_META_ADS",
        "subject": "export order checkout for us buyers",
        "body_text": (
            "Looked at your fabric store.\n"
            "Your goods match top world brands, but your international checkout gives foreign buyers currency trouble.\n"
            "You lose wholesale buyers when freight prices require manual email replies.\n"
            "We built a clean global checkout showing live freight costs and card payments.\n"
            "Are you against checking out the short video demo?"
        ),
    },
    # 12. PHASE 2 EXPANSION (Google Search + Organic Social + Retainer)
    {
        "id": "PHASE2_EXPANSION_OMNICHANNEL",
        "region": "US",
        "track": "TRACK_C_DUAL_STACK",
        "subject": "scaling past meta ad fatigue",
        "body_text": (
            "Looked at your brand search.\n"
            "Your Meta ads work well, but your competitors currently bid on your brand name across Google Search with no defense.\n"
            "You lose high-intent buyers who search your name after seeing your Instagram ads.\n"
            "We set up a safe search plan with a dynamic landing page that protects your sales.\n"
            "Are you against reviewing the thirty-second breakdown?"
        ),
    },
]

# Validation at import time to enforce Zero-Drift Invariant 6
for example in GOLDEN_EMAIL_BANK:
    VerifiedHumanEmail(
        subject=example["subject"],
        body_text=example["body_text"],
        minhash_jaccard_max=0.0,
        five_gram_overlap_pct=0.0,
    )

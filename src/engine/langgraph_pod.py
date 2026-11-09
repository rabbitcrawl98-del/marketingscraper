from __future__ import annotations
from typing import Any, Dict, List, TypedDict
try:
    from langgraph.graph import END, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    END = "END"

from src.engine.monetization_challenger import MonetizationAndPersonalizationChallenger
from src.engine.plagiarism_guard import PlagiarismAndFingerprintGuard, VerifiedHumanEmail
from src.schemas.prospect import InternetPresenceDossier, LeadInput


class OutboundPodState(TypedDict):
    lead: Dict[str, Any]
    dossier: Dict[str, Any]
    monetization_audit: Dict[str, Any]
    track: str
    region: str
    draft_subject: str
    draft_body: str
    word_count: int
    flesch_grade: float
    burstiness_sd: float
    jaccard_score: float
    validation_errors: List[str]
    iteration_count: int
    is_approved_by_critic: bool


plagiarism_guard = PlagiarismAndFingerprintGuard(jaccard_ceiling=0.35, num_perm=128)
challenger_engine = MonetizationAndPersonalizationChallenger(plagiarism_guard=plagiarism_guard)


def diagnose_and_self_challenge_node(state: OutboundPodState) -> OutboundPodState:
    dossier_dict = state.get("dossier", {})
    lead_dict = state.get("lead", {})

    active_ads = int(dossier_dict.get("active_meta_ads_count", 0))
    has_capi = bool(dossier_dict.get("has_server_capi", False))
    lcp_ms = int(dossier_dict.get("website_lcp_ms", 3200))

    if active_ads >= 2 and (not has_capi or lcp_ms > 2400):
        state["track"] = "TRACK_A_META_ADS"
    elif active_ads == 0:
        state["track"] = "TRACK_B_DEV_AUTOMATION"
    else:
        state["track"] = "TRACK_C_DUAL_STACK"

    lead_obj = LeadInput(
        company_name=lead_dict.get("company_name", "Brand"),
        domain=lead_dict.get("domain", "example.com"),
        region=state.get("region", "INDIA"),
        city=lead_dict.get("city", "Mumbai"),
        niche=lead_dict.get("niche", "Luxury Medspa Clinic"),
        first_name=lead_dict.get("first_name", "Founder"),
        last_name=lead_dict.get("last_name", ""),
        email=lead_dict.get("email", ""),
        phone_whatsapp=lead_dict.get("phone_whatsapp", ""),
        physical_address=lead_dict.get("physical_address", ""),
    )
    dossier_obj = InternetPresenceDossier(**{
        k: v for k, v in dossier_dict.items() if k in getattr(InternetPresenceDossier, "model_fields", getattr(InternetPresenceDossier, "__fields__", {}))
    })

    audit = challenger_engine.run_brutal_monetization_audit(lead=lead_obj, dossier=dossier_obj)
    state["monetization_audit"] = audit.model_dump()
    return state


async def draft_human_email_node(state: OutboundPodState) -> OutboundPodState:
    lead_dict = state["lead"]
    dossier_dict = state["dossier"]
    audit_dict = state["monetization_audit"]

    lead_obj = LeadInput(
        company_name=lead_dict.get("company_name", "Brand"),
        domain=lead_dict.get("domain", "example.com"),
        region=state.get("region", "INDIA"),
        city=lead_dict.get("city", "Mumbai"),
        niche=lead_dict.get("niche", "Luxury Medspa Clinic"),
        first_name=lead_dict.get("first_name", "Founder"),
        last_name=lead_dict.get("last_name", ""),
        email=lead_dict.get("email", ""),
        phone_whatsapp=lead_dict.get("phone_whatsapp", ""),
        physical_address=lead_dict.get("physical_address", ""),
    )
    dossier_obj = InternetPresenceDossier(**{
        k: v for k, v in dossier_dict.items() if k in getattr(InternetPresenceDossier, "model_fields", getattr(InternetPresenceDossier, "__fields__", {}))
    })
    from src.schemas.prospect import BrutalMonetizationAudit
    audit_obj = BrutalMonetizationAudit(**audit_dict)

    cand_id = str(lead_dict.get("id", f"lead-{lead_obj.domain}"))
    result = await challenger_engine.generate_verified_personalized_email(
        lead=lead_obj,
        dossier=dossier_obj,
        audit=audit_obj,
        candidate_id=cand_id,
    )

    state["draft_subject"] = result["subject"]
    state["draft_body"] = result["body_text"]
    state["word_count"] = result["word_count"]
    state["flesch_grade"] = result["flesch_grade"]
    state["burstiness_sd"] = result["burstiness_sd"]
    state["jaccard_score"] = result["jaccard_score"]
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    return state


def critic_three_gates_node(state: OutboundPodState) -> OutboundPodState:
    try:
        VerifiedHumanEmail(
            subject=state["draft_subject"],
            body_text=state["draft_body"],
            minhash_jaccard_max=state.get("jaccard_score", 0.05),
            five_gram_overlap_pct=0.0,
        )
        state["is_approved_by_critic"] = True
        state["validation_errors"] = []
    except Exception as exc:
        state["is_approved_by_critic"] = False
        state["validation_errors"] = [str(exc)]
    return state


def route_after_critic(state: OutboundPodState) -> str:
    if state.get("is_approved_by_critic"):
        return END
    if state.get("iteration_count", 0) >= 3:
        return END
    return "draft_human_email"


class _FallbackPodRunner:
    async def ainvoke(self, state: OutboundPodState) -> OutboundPodState:
        state = diagnose_and_self_challenge_node(state)
        for _ in range(3):
            state = await draft_human_email_node(state)
            state = critic_three_gates_node(state)
            if route_after_critic(state) == END:
                break
        return state


def build_outbound_langgraph_pod():
    if not HAS_LANGGRAPH:
        return _FallbackPodRunner()
    workflow = StateGraph(OutboundPodState)
    workflow.add_node("diagnose_bottleneck", diagnose_and_self_challenge_node)
    workflow.add_node("draft_human_email", draft_human_email_node)
    workflow.add_node("critic_three_gates", critic_three_gates_node)

    workflow.set_entry_point("diagnose_bottleneck")
    workflow.add_edge("diagnose_bottleneck", "draft_human_email")
    workflow.add_edge("draft_human_email", "critic_three_gates")
    workflow.add_conditional_edges("critic_three_gates", route_after_critic)
    return workflow.compile()

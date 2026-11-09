from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
try:
    from pydantic import ConfigDict
    HAS_PYDANTIC_V2 = True
except ImportError:
    HAS_PYDANTIC_V2 = False
    def ConfigDict(**kwargs): return kwargs


class RegionEnum(str, Enum):
    INDIA = "INDIA"
    US = "US"
    EU = "EU"
    UK = "UK"
    GULF = "GULF"
    AUSTRALIA = "AUSTRALIA"
    CANADA = "CANADA"
    SINGAPORE = "SINGAPORE"
    PAKISTAN = "PAKISTAN"


class EmailStatusEnum(str, Enum):
    VALID = "VALID"
    CATCH_ALL = "CATCH_ALL"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class BottleneckTrackEnum(str, Enum):
    TRACK_A_META_ADS = "TRACK_A_META_ADS"
    TRACK_B_DEV_AUTOMATION = "TRACK_B_DEV_AUTOMATION"
    TRACK_C_DUAL_STACK = "TRACK_C_DUAL_STACK"


class CampaignStatusEnum(str, Enum):
    PENDING_HITL = "PENDING_HITL"
    APPROVED_QUEUED = "APPROVED_QUEUED"
    ACTIVE_SENDING = "ACTIVE_SENDING"
    REPLIED_PAUSED = "REPLIED_PAUSED"
    BOUNCED = "BOUNCED"
    REJECTED = "REJECTED"


class LeadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(..., min_length=1, description="Company name")
    domain: str = Field(..., min_length=3, description="Target company website domain")
    region: RegionEnum = Field(default=RegionEnum.INDIA, description="Geographic operating region")
    city: str = Field(default="Mumbai", description="Target city")
    niche: str = Field(default="Luxury Medspa Clinic", description="Business category or vertical")
    first_name: Optional[str] = Field(default=None, description="Known founder first name")
    last_name: Optional[str] = Field(default=None, description="Known founder last name")
    email: Optional[str] = Field(default=None, description="Known email if pre-provided")
    phone_whatsapp: Optional[str] = Field(default="", description="WhatsApp or business contact phone")
    physical_address: Optional[str] = Field(default="", description="Street address or locality")
    linkedin_url: Optional[str] = Field(default="", description="LinkedIn profile or company URL")


class OSINTContactResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    email_status: EmailStatusEnum
    first_name: str
    last_name: str
    title: str = "Founder & Managing Director"
    linkedin_url: str = ""
    phone_whatsapp: str = ""
    physical_address: str = ""
    verification_detail: str


class InternetPresenceDossier(BaseModel):
    model_config = ConfigDict(extra="ignore")

    domain: str = Field(default="", description="Target company website domain")
    website_reachable: bool = Field(default=True, description="Whether website domain responds over HTTP")
    website_lcp_ms: int = Field(default=3200, ge=0, description="Mobile LCP load speed in ms")
    mobile_pagespeed_score: int = Field(default=65, ge=0, le=100, description="Mobile PageSpeed score")
    has_meta_pixel: bool = Field(default=False, description="Whether Meta Pixel is installed")
    has_server_capi: bool = Field(default=False, description="Whether Meta Server-Side CAPI is active")
    has_gtm: bool = Field(default=False, description="Whether Google Tag Manager is installed")
    has_google_tag: bool = Field(default=False, description="Whether Google Analytics / GTAG is active")
    has_whatsapp_widget: bool = Field(default=False, description="Whether click-to-WhatsApp widget is active")
    has_instant_booking: bool = Field(default=False, description="Whether instant calendar/booking widget exists")
    active_ads_count: int = Field(default=0, ge=0, description="Number of active ad campaigns")
    active_meta_ads_count: int = Field(default=0, ge=0, description="Number of currently active Meta Ads")
    ad_library_hook_summary: str = Field(default="", description="Summary of current ad creative hooks")
    website_title: str = Field(default="", description="Scraped HTML <title> of the business")
    website_h1: str = Field(default="", description="Scraped primary H1 headline")
    detected_services: List[str] = Field(default_factory=list, description="Specific services or products extracted")
    detected_leaks: List[str] = Field(default_factory=list, description="Specific conversion/technical leaks identified")
    recent_linkedin_post: str = Field(default="", description="Recent public LinkedIn post or update")
    customer_review_pain: str = Field(default="", description="Voice-of-customer complaint from 1-3 star reviews")
    open_job_roles: str = Field(default="", description="Open hiring positions or talent bottlenecks")
    tech_stack: List[str] = Field(default_factory=list, description="Detected CMS/E-Com/Frontend stack")
    scraped_website_excerpt: str = Field(default="", description="Pruned markdown excerpt from website")
    primary_bottleneck_track: BottleneckTrackEnum = Field(default=BottleneckTrackEnum.TRACK_A_META_ADS)


class BrutalMonetizationAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deal_viability_score: int = Field(..., ge=0, le=100, description="0-100 brutal deal viability score")
    deal_classification: str = Field(..., description="e.g. HIGH-TICKET WHALE, FAST-CASH MID-MARKET, or LOW-MARGIN SKIP")
    brutal_honest_assessment: str = Field(..., description="Unfiltered big-brother truth on why they leak money and if they can pay")
    self_challenge_critique: str = Field(..., description="Skeptical buyer critique of why a generic pitch fails and how our angle wins")
    quantified_monthly_leak: str = Field(..., description="Deterministic monthly revenue bleed calculation (COI)")
    foot_in_door_48h_offer: str = Field(..., description="Low-friction 48h cashflow wedge offer they say yes to immediately")
    foot_in_door_price: str = Field(..., description="Exact regional price for 48h wedge")
    core_transformation_offer: str = Field(..., description="14-day full-stack / growth engine scope")
    core_transformation_price: str = Field(..., description="Exact Tier 1/2 regional price")
    monthly_retainer_offer: str = Field(..., description="Recurring monthly retainer scope & price")
    zero_friction_proof_gift: str = Field(..., description="Exact free micro-asset/preview to send right now to close them")
    why_they_pay_without_objection: str = Field(..., description="Psychological + mathematical trigger that eliminates price resistance")


class BottleneckDiagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track: BottleneckTrackEnum
    primary_revenue_leak: str
    proposed_solution: str
    suggested_offer_anchor: str

# Add model_dump compatibility for Pydantic v1
if not hasattr(BaseModel, "model_dump"):
    BaseModel.model_dump = lambda self, **kwargs: self.dict(**kwargs)
if not hasattr(BaseModel, "model_fields"):
    BaseModel.model_fields = property(lambda self: self.__fields__)

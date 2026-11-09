CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE OR REPLACE FUNCTION uuid_generate_v7() RETURNS uuid AS $$
DECLARE
    v_time timestamp with time zone := clock_timestamp();
    v_secs bigint := EXTRACT(EPOCH FROM v_time);
    v_msec bigint := MOD(EXTRACT(MILLISECONDS FROM v_time)::bigint, 1000);
    v_unix_t bigint := (v_secs * 1000) + v_msec;
    v_rand bytea := gen_random_bytes(10);
    v_uuid bytea;
BEGIN
    v_uuid := set_byte(decode(lpad(to_hex(v_unix_t), 12, '0'), 'hex') || v_rand, 6, (get_byte(v_rand, 0) & 15) | 112);
    v_uuid := set_byte(v_uuid, 8, (get_byte(v_rand, 2) & 63) | 128);
    RETURN encode(v_uuid, 'hex')::uuid;
END;
$$ LANGUAGE plpgsql VOLATILE;

DO $$ BEGIN
    CREATE TYPE region_enum AS ENUM ('INDIA', 'US', 'EU', 'UK', 'GULF', 'AUSTRALIA', 'CANADA', 'SINGAPORE', 'PAKISTAN');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE email_status_enum AS ENUM ('VALID', 'CATCH_ALL', 'INVALID', 'UNKNOWN');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE bottleneck_track_enum AS ENUM ('TRACK_A_META_ADS', 'TRACK_B_DEV_AUTOMATION', 'TRACK_C_DUAL_STACK');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE campaign_status_enum AS ENUM ('PENDING_HITL', 'APPROVED_QUEUED', 'ACTIVE_SENDING', 'REPLIED_PAUSED', 'BOUNCED', 'REJECTED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE webhook_lease_status_enum AS ENUM ('PROCESSING', 'COMPLETED', 'FAILED_DLQ');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-7000-8000-000000000001'::uuid,
    email VARCHAR(320) NOT NULL,
    email_status email_status_enum NOT NULL DEFAULT 'UNKNOWN',
    verification_method VARCHAR(64) NOT NULL DEFAULT 'HYBRID_OSINT',
    first_name VARCHAR(120) NOT NULL,
    last_name VARCHAR(120) DEFAULT '',
    title VARCHAR(180) DEFAULT 'Founder',
    company_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    linkedin_url TEXT DEFAULT '',
    phone_whatsapp VARCHAR(64) DEFAULT '',
    physical_address TEXT DEFAULT '',
    area VARCHAR(180) DEFAULT '',
    pincode VARCHAR(32) DEFAULT '',
    city VARCHAR(120) DEFAULT '',
    state VARCHAR(120) DEFAULT '',
    country VARCHAR(120) DEFAULT 'India',
    client_tier VARCHAR(64) DEFAULT 'ALL_TIERS',
    region region_enum NOT NULL DEFAULT 'INDIA',
    domain_sha256 CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, email)
);

CREATE TABLE IF NOT EXISTS prospect_dossiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-7000-8000-000000000001'::uuid,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    website_lcp_ms INTEGER DEFAULT 3200,
    has_meta_pixel BOOLEAN DEFAULT FALSE,
    has_server_capi BOOLEAN DEFAULT FALSE,
    has_gtm BOOLEAN DEFAULT FALSE,
    has_whatsapp_widget BOOLEAN DEFAULT FALSE,
    has_instant_booking BOOLEAN DEFAULT FALSE,
    active_meta_ads_count INTEGER DEFAULT 0,
    ad_library_hook_summary TEXT DEFAULT '',
    recent_linkedin_post TEXT DEFAULT '',
    customer_review_pain TEXT DEFAULT '',
    open_job_roles TEXT DEFAULT '',
    tech_stack JSONB DEFAULT '[]'::jsonb,
    detected_services JSONB DEFAULT '[]'::jsonb,
    detected_leaks JSONB DEFAULT '[]'::jsonb,
    scraped_website_excerpt TEXT DEFAULT '',
    primary_bottleneck_track bottleneck_track_enum NOT NULL DEFAULT 'TRACK_A_META_ADS',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS smtp_mailboxes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-7000-8000-000000000001'::uuid,
    email_address VARCHAR(320) NOT NULL UNIQUE,
    sender_display_name VARCHAR(120) NOT NULL,
    smtp_host VARCHAR(255) NOT NULL,
    smtp_port INTEGER NOT NULL DEFAULT 587,
    imap_host VARCHAR(255) NOT NULL,
    imap_port INTEGER NOT NULL DEFAULT 993,
    username VARCHAR(320) NOT NULL,
    app_password TEXT NOT NULL,
    daily_limit INTEGER NOT NULL DEFAULT 25,
    sent_today INTEGER NOT NULL DEFAULT 0,
    bounced_today INTEGER NOT NULL DEFAULT 0,
    warmup_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS outreach_emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-7000-8000-000000000001'::uuid,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    mailbox_id UUID REFERENCES smtp_mailboxes(id),
    touch_number SMALLINT NOT NULL CHECK (touch_number BETWEEN 1 AND 4),
    subject TEXT NOT NULL,
    body_text TEXT NOT NULL,
    word_count SMALLINT NOT NULL,
    flesch_grade NUMERIC(4,2) NOT NULL DEFAULT 5.50,
    burstiness_sd NUMERIC(5,2) NOT NULL,
    minhash_jaccard_max NUMERIC(4,3) NOT NULL DEFAULT 0.000,
    five_gram_overlap_pct NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    rfc_message_id VARCHAR(255),
    in_reply_to_message_id VARCHAR(255),
    status campaign_status_enum NOT NULL DEFAULT 'PENDING_HITL',
    scheduled_send_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_minhash_index (
    email_id UUID PRIMARY KEY REFERENCES outreach_emails(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-7000-8000-000000000001'::uuid,
    shingles_5gram JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS webhook_event_leases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id UUID NOT NULL DEFAULT '00000000-0000-7000-8000-000000000001'::uuid,
    provider VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    status webhook_lease_status_enum NOT NULL DEFAULT 'PROCESSING',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_detail TEXT DEFAULT '',
    attempts SMALLINT NOT NULL DEFAULT 1,
    leased_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE (provider, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_leads_tenant_region ON leads(tenant_id, region, email_status);
CREATE INDEX IF NOT EXISTS idx_leads_domain_sha256 ON leads(domain_sha256);
CREATE INDEX IF NOT EXISTS idx_outreach_status_sched ON outreach_emails(tenant_id, status, scheduled_send_at);
CREATE INDEX IF NOT EXISTS idx_webhook_leases_status ON webhook_event_leases(tenant_id, status, leased_at);

-- Enable & Force Row-Level Security + Explicit Tenant Isolation Policies
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_leads ON leads
        USING (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id))
        WITH CHECK (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id));
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE prospect_dossiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE prospect_dossiers FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_dossiers ON prospect_dossiers
        USING (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id))
        WITH CHECK (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id));
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE smtp_mailboxes ENABLE ROW LEVEL SECURITY;
ALTER TABLE smtp_mailboxes FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_mailboxes ON smtp_mailboxes
        USING (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id))
        WITH CHECK (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id));
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE outreach_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE outreach_emails FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_emails ON outreach_emails
        USING (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id))
        WITH CHECK (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id));
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE email_minhash_index ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_minhash_index FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_minhash ON email_minhash_index
        USING (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id))
        WITH CHECK (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id));
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE webhook_event_leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_event_leases FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_webhook_leases ON webhook_event_leases
        USING (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id))
        WITH CHECK (tenant_id = COALESCE(NULLIF(current_setting('app.current_tenant_id', true), '')::uuid, tenant_id));
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

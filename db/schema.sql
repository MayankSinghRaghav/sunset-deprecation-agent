-- Sunset schema. Single Postgres database, no second datastore (spec §6).
--
-- Embedding columns are added at the bottom by a DO block that detects whether
-- the `vector` extension is present, so this file applies cleanly on a cluster
-- where the pgvector apt install failed. See scripts/pg_bootstrap.sh.

-- ===========================================================================
-- Catalogue and evidence — this is everything the agent is allowed to read.
--
-- Note what is NOT here: no trap_class, no correct_verdict, no "is_seasonal"
-- convenience column. Every trap must be *derived* from evidence. A label
-- column anywhere in this section would make the whole evaluation circular.
-- datagen/lint.py greps the generated fixtures to enforce that.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS features (
    id                      text PRIMARY KEY,
    name                    text NOT NULL,
    description             text NOT NULL,
    area                    text NOT NULL,
    launched_at             date NOT NULL,
    maintenance_cost_band   text NOT NULL
        CHECK (maintenance_cost_band IN ('low', 'medium', 'high')),
    annual_maintenance_usd  integer NOT NULL,
    -- Drives the migration-plan rule: the composer proposes a concrete plan
    -- only when a replacement exists, and states the requirement otherwise.
    -- DEFERRABLE so fixture loading (which inserts features in id order) can
    -- reference a replacement that is inserted later in the same transaction.
    replacement_feature_id  text
        REFERENCES features (id) DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS feature_dependencies (
    from_feature_id text NOT NULL REFERENCES features (id),
    to_feature_id   text NOT NULL REFERENCES features (id),
    kind            text NOT NULL CHECK (kind IN ('calls', 'reads_from', 'renders_in', 'auth_via')),
    PRIMARY KEY (from_feature_id, to_feature_id),
    CHECK (from_feature_id <> to_feature_id)
);

CREATE TABLE IF NOT EXISTS accounts (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    arr_band    text NOT NULL CHECK (arr_band IN ('whale', 'mid_market', 'smb')),
    arr_usd     integer NOT NULL,
    segment     text NOT NULL,
    industry    text NOT NULL,
    signed_at   date NOT NULL
);

-- Daily aggregates, not raw events (spec §4.2): keeps the DB small and forces
-- the seasonality signal to be real rather than an artifact of sampling.
CREATE TABLE IF NOT EXISTS usage_daily (
    feature_id   text NOT NULL REFERENCES features (id),
    account_id   text NOT NULL REFERENCES accounts (id),
    day          date NOT NULL,
    -- 'human' vs 'bot'/'internal_qa' is the entire trap-6 signal. Any code path
    -- that sums across actor_type without filtering will read phantom usage as
    -- real demand.
    actor_type   text NOT NULL CHECK (actor_type IN ('human', 'bot', 'internal_qa')),
    active_users integer NOT NULL,
    events       integer NOT NULL,
    PRIMARY KEY (feature_id, account_id, day, actor_type)
);

CREATE TABLE IF NOT EXISTS support_tickets (
    id               text PRIMARY KEY,
    account_id       text NOT NULL REFERENCES accounts (id),
    -- "guess" is deliberate: real ticket routing is lossy, and the Support
    -- auditor should not be handed a perfect feature join.
    feature_id_guess text REFERENCES features (id),
    created_at       timestamptz NOT NULL,
    subject          text NOT NULL,
    body             text NOT NULL,
    resolution       text
);

CREATE TABLE IF NOT EXISTS contracts (
    id             text PRIMARY KEY,
    account_id     text NOT NULL REFERENCES accounts (id),
    title          text NOT NULL,
    effective_from date NOT NULL,
    expires_at     date NOT NULL
);

-- Obligations are phrased as capabilities, never as product feature names
-- (spec §4.2). "Customer shall retain the ability to export transaction records
-- in a machine-readable format" — not "Customer shall retain CSV Export".
-- This is what defeats keyword grep and justifies semantic retrieval; the
-- deterministic baseline is *designed* to fail here.
CREATE TABLE IF NOT EXISTS contract_clauses (
    id          text PRIMARY KEY,
    contract_id text NOT NULL REFERENCES contracts (id),
    section     text NOT NULL,
    text        text NOT NULL
);

CREATE TABLE IF NOT EXISTS deal_notes (
    id         text PRIMARY KEY,
    account_id text NOT NULL REFERENCES accounts (id),
    outcome    text NOT NULL CHECK (outcome IN ('won', 'lost')),
    closed_at  date NOT NULL,
    body       text NOT NULL
);

-- ===========================================================================
-- Audit records
-- ===========================================================================

CREATE TABLE IF NOT EXISTS audit_runs (
    id            text PRIMARY KEY,
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz,
    status        text NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'failed', 'awaiting_review')),
    model_config  jsonb NOT NULL DEFAULT '{}'::jsonb,
    -- Set when any call in the run used the offline stub. eval/score.py refuses
    -- to print an accuracy headline for such a run.
    used_offline_stub boolean NOT NULL DEFAULT false,
    cost_tokens   integer NOT NULL DEFAULT 0,
    latency_ms    integer NOT NULL DEFAULT 0,
    features_total     integer NOT NULL DEFAULT 0,
    features_completed integer NOT NULL DEFAULT 0,
    error         text
);

CREATE TABLE IF NOT EXISTS feature_audits (
    id          text PRIMARY KEY,
    run_id      text NOT NULL REFERENCES audit_runs (id) ON DELETE CASCADE,
    feature_id  text NOT NULL REFERENCES features (id),
    status      text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'awaiting_review',
                          'completed', 'citation_failed', 'failed')),
    verdict     text CHECK (verdict IN ('KILL', 'MIGRATE', 'KEEP', 'FIX', 'ESCALATE')),
    -- Spec §2 says trap 7's right answer is "keep, reclassify as sales
    -- collateral, stop investing" — which the five-value vocabulary cannot
    -- express. Rather than add a sixth verdict, the reclassification rides
    -- alongside. Trap 7 scores as verdict=KEEP AND this = RECLASSIFY_SALES_COLLATERAL.
    secondary_action text CHECK (secondary_action IN (
        'RECLASSIFY_SALES_COLLATERAL', 'FREEZE_INVESTMENT', 'MONITOR_NEXT_QUARTER')),
    confidence  text CHECK (confidence IN ('high', 'medium', 'low')),
    prefilter_verdict text CHECK (prefilter_verdict IN ('candidate', 'obvious_keep')),
    -- Never empty, never suppressed (spec §5.3). If no counter-argument exists
    -- the composer must say so explicitly rather than omit the field.
    dissent     text,
    memo_markdown text,
    applied_rules jsonb NOT NULL DEFAULT '[]'::jsonb,
    disagreements jsonb NOT NULL DEFAULT '[]'::jsonb,
    reflection_passes integer NOT NULL DEFAULT 0 CHECK (reflection_passes <= 1),
    state_json  jsonb NOT NULL DEFAULT '{}'::jsonb,
    thread_id   text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, feature_id)
);

-- The table that separates this from a summarisation demo (spec §6). Every
-- factual claim in a memo carries an evidence ref; the citation validator
-- resolves each one against its source row and verifies the quoted span.
CREATE TABLE IF NOT EXISTS evidence_refs (
    id               text PRIMARY KEY,
    feature_audit_id text NOT NULL REFERENCES feature_audits (id) ON DELETE CASCADE,
    source_table     text NOT NULL CHECK (source_table IN (
        'usage_daily', 'support_tickets', 'contract_clauses',
        'deal_notes', 'features', 'feature_dependencies', 'accounts')),
    source_id        text NOT NULL,
    claim_text       text NOT NULL,
    quoted_span      text,
    resolved         boolean,
    resolution_error text
);

CREATE TABLE IF NOT EXISTS human_overrides (
    id               text PRIMARY KEY,
    feature_audit_id text NOT NULL REFERENCES feature_audits (id) ON DELETE CASCADE,
    kind             text NOT NULL CHECK (kind IN ('decision', 'fact')),
    original_verdict text,
    new_verdict      text CHECK (new_verdict IN ('KILL', 'MIGRATE', 'KEEP', 'FIX', 'ESCALATE')),
    -- Invalidated auditor for a 'fact' override, so resume re-runs one auditor
    -- rather than all four.
    target_auditor   text CHECK (target_auditor IN ('usage', 'contract', 'support', 'revenue')),
    reason           text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- ===========================================================================
-- Instrumentation. Not in the spec's table list, but §3.3 asks for per-agent
-- cost and latency, which is unmeasurable without it.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS llm_calls (
    id            bigserial PRIMARY KEY,
    run_id        text,
    feature_id    text,
    agent         text NOT NULL,
    provider      text NOT NULL,          -- gemini | replay | offline
    model_id      text NOT NULL,
    prompt_version text NOT NULL,
    request_hash  text NOT NULL,
    prompt_tokens integer NOT NULL DEFAULT 0,
    output_tokens integer NOT NULL DEFAULT 0,
    latency_ms    integer NOT NULL DEFAULT 0,
    cache_hit     boolean NOT NULL DEFAULT false,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- The (feature_id, evidence_hash) cache from spec §9.3. Kept separate from the
-- LangGraph checkpointer on purpose: checkpoints are thread-scoped, so they
-- cannot serve reuse across runs, which is the whole point of the lever.
-- prompt_version in the key means editing the composer prompt costs zero
-- auditor tokens on the next run.
CREATE TABLE IF NOT EXISTS auditor_cache (
    cache_key      text PRIMARY KEY,
    feature_id     text NOT NULL,
    evidence_hash  text NOT NULL,
    auditor        text NOT NULL,
    prompt_version text NOT NULL,
    model_id       text NOT NULL,
    output_json    jsonb NOT NULL,
    prompt_tokens  integer NOT NULL DEFAULT 0,
    output_tokens  integer NOT NULL DEFAULT 0,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- ===========================================================================
-- Embedding columns — shape depends on whether pgvector is installed.
-- ===========================================================================

DO $$
DECLARE
    has_vector boolean := EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector');
    coltype    text    := CASE WHEN has_vector THEN 'vector(768)' ELSE 'real[]' END;
    t          text;
BEGIN
    FOREACH t IN ARRAY ARRAY['support_tickets', 'contract_clauses', 'deal_notes'] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = t AND column_name = 'embedding'
        ) THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN embedding %s', t, coltype);
        END IF;
        -- Retrieval filters on this so a hashing vector can never be cosined
        -- against a Gemini one.
        EXECUTE format(
            'ALTER TABLE %I ADD COLUMN IF NOT EXISTS embedding_model text', t);
    END LOOP;
END $$;

-- Ownership: the bootstrap runs as `postgres`, so tables are superuser-owned
-- and ALTER DEFAULT PRIVILEGES (which is per-creating-role) does not apply.
-- Grant explicitly. TRUNCATE is included so `make seed` can reset the evidence
-- tables as the app role (public schema only — never touches schema truth).
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public
    TO sunset_app, sunset_eval;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sunset_app, sunset_eval;

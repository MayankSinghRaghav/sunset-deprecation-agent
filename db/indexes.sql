-- Indexes. Split from schema.sql so fixture loading can defer them.

CREATE INDEX IF NOT EXISTS ix_usage_feature_day    ON usage_daily (feature_id, day);
CREATE INDEX IF NOT EXISTS ix_usage_feature_actor  ON usage_daily (feature_id, actor_type);
CREATE INDEX IF NOT EXISTS ix_usage_account        ON usage_daily (account_id);

CREATE INDEX IF NOT EXISTS ix_tickets_feature      ON support_tickets (feature_id_guess);
CREATE INDEX IF NOT EXISTS ix_tickets_created      ON support_tickets (created_at);
CREATE INDEX IF NOT EXISTS ix_clauses_contract     ON contract_clauses (contract_id);
CREATE INDEX IF NOT EXISTS ix_deal_notes_outcome   ON deal_notes (outcome);
CREATE INDEX IF NOT EXISTS ix_contracts_account    ON contracts (account_id);

CREATE INDEX IF NOT EXISTS ix_audits_run           ON feature_audits (run_id);
CREATE INDEX IF NOT EXISTS ix_evidence_audit       ON evidence_refs (feature_audit_id);
CREATE INDEX IF NOT EXISTS ix_llm_calls_run        ON llm_calls (run_id, agent);
CREATE INDEX IF NOT EXISTS ix_auditor_cache_lookup ON auditor_cache (feature_id, auditor);

-- Vector indexes only when pgvector is present.
--
-- HNSW over IVFFlat here: IVFFlat needs a populated table to build meaningful
-- lists, and at ~1,500 rows the list count would be so small the index degrades
-- to a scan anyway. HNSW builds fine on an empty table and is exact enough at
-- this scale. (At 1,500 vectors a sequential scan is also fine — the index is
-- for shape, not speed.)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_tickets_embedding
                 ON support_tickets USING hnsw (embedding vector_cosine_ops)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_clauses_embedding
                 ON contract_clauses USING hnsw (embedding vector_cosine_ops)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS ix_deal_notes_embedding
                 ON deal_notes USING hnsw (embedding vector_cosine_ops)';
    END IF;
END $$;

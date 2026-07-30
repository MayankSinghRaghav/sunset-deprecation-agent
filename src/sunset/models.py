"""SQLAlchemy ORM. One file because the 14 tables interlock.

schema.sql is the source of truth (no Alembic). tests/test_schema.py reflects the
live database and asserts these models match it, so the two cannot silently drift.

Embedding columns are intentionally NOT mapped as typed vector columns here: the
column type is `vector(768)` or `real[]` depending on whether pgvector installed,
and retrieval goes through evidence/retrieval.py which handles both. The ORM does
not need to read embeddings.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Catalogue + evidence
# ---------------------------------------------------------------------------


class Feature(Base):
    __tablename__ = "features"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    area: Mapped[str] = mapped_column(Text)
    launched_at: Mapped[date] = mapped_column(Date)
    maintenance_cost_band: Mapped[str] = mapped_column(Text)
    annual_maintenance_usd: Mapped[int] = mapped_column(Integer)
    replacement_feature_id: Mapped[str | None] = mapped_column(
        ForeignKey("features.id"), nullable=True
    )


class FeatureDependency(Base):
    __tablename__ = "feature_dependencies"
    from_feature_id: Mapped[str] = mapped_column(
        ForeignKey("features.id"), primary_key=True
    )
    to_feature_id: Mapped[str] = mapped_column(
        ForeignKey("features.id"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(Text)


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    arr_band: Mapped[str] = mapped_column(Text)
    arr_usd: Mapped[int] = mapped_column(Integer)
    segment: Mapped[str] = mapped_column(Text)
    industry: Mapped[str] = mapped_column(Text)
    signed_at: Mapped[date] = mapped_column(Date)


class UsageDaily(Base):
    __tablename__ = "usage_daily"
    feature_id: Mapped[str] = mapped_column(
        ForeignKey("features.id"), primary_key=True
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    actor_type: Mapped[str] = mapped_column(Text, primary_key=True)
    active_users: Mapped[int] = mapped_column(Integer)
    events: Mapped[int] = mapped_column(Integer)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    feature_id_guess: Mapped[str | None] = mapped_column(
        ForeignKey("features.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)


class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    title: Mapped[str] = mapped_column(Text)
    effective_from: Mapped[date] = mapped_column(Date)
    expires_at: Mapped[date] = mapped_column(Date)


class ContractClause(Base):
    __tablename__ = "contract_clauses"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"))
    section: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)


class DealNote(Base):
    __tablename__ = "deal_notes"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    outcome: Mapped[str] = mapped_column(Text)
    closed_at: Mapped[date] = mapped_column(Date)
    body: Mapped[str] = mapped_column(Text)
    embedding_model: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Audit records
# ---------------------------------------------------------------------------


class AuditRun(Base):
    __tablename__ = "audit_runs"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, server_default=text("'running'"))
    model_config_json: Mapped[dict] = mapped_column(
        "model_config", JSONB, server_default=text("'{}'::jsonb")
    )
    used_offline_stub: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false")
    )
    cost_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    latency_ms: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    features_total: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    features_completed: Mapped[int] = mapped_column(
        Integer, server_default=text("0")
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    audits: Mapped[list[FeatureAudit]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class FeatureAudit(Base):
    __tablename__ = "feature_audits"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("audit_runs.id", ondelete="CASCADE")
    )
    feature_id: Mapped[str] = mapped_column(ForeignKey("features.id"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    verdict: Mapped[str | None] = mapped_column(Text, nullable=True)
    secondary_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    prefilter_verdict: Mapped[str | None] = mapped_column(Text, nullable=True)
    dissent: Mapped[str | None] = mapped_column(Text, nullable=True)
    memo_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_rules: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    disagreements: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    reflection_passes: Mapped[int] = mapped_column(
        Integer, server_default=text("0")
    )
    state_json: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    thread_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    run: Mapped[AuditRun] = relationship(back_populates="audits")
    evidence: Mapped[list[EvidenceRefRow]] = relationship(
        back_populates="audit", cascade="all, delete-orphan"
    )


class EvidenceRefRow(Base):
    __tablename__ = "evidence_refs"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    feature_audit_id: Mapped[str] = mapped_column(
        ForeignKey("feature_audits.id", ondelete="CASCADE")
    )
    source_table: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(Text)
    claim_text: Mapped[str] = mapped_column(Text)
    quoted_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    resolution_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    audit: Mapped[FeatureAudit] = relationship(back_populates="evidence")


class HumanOverride(Base):
    __tablename__ = "human_overrides"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    feature_audit_id: Mapped[str] = mapped_column(
        ForeignKey("feature_audits.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(Text)
    original_verdict: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_verdict: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_auditor: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class LLMCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    request_hash: Mapped[str] = mapped_column(Text)
    prompt_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    latency_ms: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cache_hit: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class AuditorCache(Base):
    __tablename__ = "auditor_cache"
    cache_key: Mapped[str] = mapped_column(Text, primary_key=True)
    feature_id: Mapped[str] = mapped_column(Text)
    evidence_hash: Mapped[str] = mapped_column(Text)
    auditor: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str] = mapped_column(Text)
    output_json: Mapped[dict] = mapped_column(JSONB)
    prompt_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

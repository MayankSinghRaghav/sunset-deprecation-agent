"""DTOs — the shapes that cross node boundaries and get validated.

These are Pydantic models, not ORM rows. The auditors emit them, the reconciler
consumes them, the composer renders them. Keeping the wire shapes here (separate
from models.py) means the LLM's structured-output schema and the reconciler's
input are the same definition, so they cannot drift.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Verdict(StrEnum):
    KILL = "KILL"
    MIGRATE = "MIGRATE"
    KEEP = "KEEP"
    FIX = "FIX"
    ESCALATE = "ESCALATE"


class SecondaryAction(StrEnum):
    RECLASSIFY_SALES_COLLATERAL = "RECLASSIFY_SALES_COLLATERAL"
    FREEZE_INVESTMENT = "FREEZE_INVESTMENT"
    MONITOR_NEXT_QUARTER = "MONITOR_NEXT_QUARTER"


Confidence = Literal["high", "medium", "low"]
AuditorName = Literal["usage", "contract", "support", "revenue"]


class EvidenceRef(BaseModel):
    """A pointer from a claim back to the row that supports it.

    `quoted_span` must be a verbatim substring of the source row's text; the
    citation validator checks exactly that.
    """

    ref_id: str
    source_table: Literal[
        "usage_daily",
        "support_tickets",
        "contract_clauses",
        "deal_notes",
        "features",
        "feature_dependencies",
        "accounts",
    ]
    source_id: str
    claim_text: str
    quoted_span: str | None = None


class AccountRef(BaseModel):
    account_id: str
    name: str
    arr_band: Literal["whale", "mid_market", "smb"]
    reason: str


# ---------------------------------------------------------------------------
# Auditor outputs. Each auditor computes numbers in Python and asks the LLM only
# to interpret them; the interpretation lands in `finding` and `rationale`, the
# machine-checkable facts land in the typed `signals` fields.
# ---------------------------------------------------------------------------


class UsageSignals(BaseModel):
    human_trend: Literal["growing", "flat", "declining", "collapsed", "dead"]
    seasonality_detected: bool
    seasonal_period_months: int | None = None
    bot_share: float = Field(ge=0, le=1)
    phantom_usage: bool  # bot/QA inflates an otherwise-dead feature
    top1pct_arr_share: float = Field(ge=0, le=1)
    revenue_concentrated: bool
    whale_usage: bool
    active_human_accounts: int


class ContractSignals(BaseModel):
    status: Literal["obligated", "possibly_obligated", "clear"]
    matched_clause_ids: list[str] = Field(default_factory=list)
    obligated_accounts: list[str] = Field(default_factory=list)


class SupportSignals(BaseModel):
    latent_demand: bool  # people still want it (requests, "please fix")
    defect_signal: bool  # repeated failed attempts after a usage drop
    sentiment: Literal["positive", "neutral", "frustrated", "mixed"]
    ticket_count: int


class RevenueSignals(BaseModel):
    sales_critical: bool  # cited in won deals / competitive displacement
    won_deal_mentions: int
    competitive_displacement: bool


class AuditorOutput(BaseModel):
    auditor: AuditorName
    finding: str  # one-line human-readable conclusion (LLM-written)
    rationale: str  # short justification (LLM-written)
    confidence: Confidence
    signals: dict  # one of the *Signals shapes above, as a dict
    citations: list[EvidenceRef] = Field(default_factory=list)


class Disagreement(BaseModel):
    between: tuple[AuditorName, AuditorName]
    description: str


class ReconcilerResult(BaseModel):
    verdict: Verdict
    secondary_action: SecondaryAction | None = None
    confidence: Confidence
    cap: Verdict | None = None  # the strongest verdict precedence allowed
    applied_rules: list[str] = Field(default_factory=list)
    disagreements: list[Disagreement] = Field(default_factory=list)
    needs_reflection: bool = False


class Claim(BaseModel):
    text: str
    evidence_ref_ids: list[str] = Field(default_factory=list)


class Memo(BaseModel):
    verdict: Verdict
    secondary_action: SecondaryAction | None = None
    confidence: Confidence
    summary: str
    claims: list[Claim]
    at_risk_accounts: list[AccountRef] = Field(default_factory=list)
    migration_plan: str | None = None  # only when a replacement exists
    # Never empty. If there is genuinely no counter-argument, this says so
    # explicitly rather than being omitted (spec §5.3, §8.2 dissent margin).
    dissent: str


class CitationReport(BaseModel):
    total: int
    resolved: int
    unresolved_ref_ids: list[str] = Field(default_factory=list)

    @property
    def clean(self) -> bool:
        return self.total == self.resolved

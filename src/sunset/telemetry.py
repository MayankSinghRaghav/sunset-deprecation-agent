"""Token/latency ledger and the budget guard.

Per-agent token accounting is a first-class deliverable (spec §3.3), and the
budget guard is a design stance: at 150K tokens a run STOPS rather than silently
truncating evidence to fit. Truncating evidence to hit a round number is exactly
how you manufacture a catastrophic error, so we fail loudly instead.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field

import structlog

from sunset.config import settings
from sunset.errors import BudgetExceeded

log = structlog.get_logger("sunset")


@dataclass
class CallRecord:
    agent: str
    provider: str
    model_id: str
    prompt_version: str
    request_hash: str
    prompt_tokens: int
    output_tokens: int
    latency_ms: int
    cache_hit: bool
    feature_id: str | None = None


@dataclass
class Ledger:
    """Thread-safe accumulator. The four auditors write to it concurrently."""

    budget: int = field(default_factory=lambda: settings.token_budget)
    records: list[CallRecord] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    used_offline: bool = False

    def record(self, r: CallRecord) -> None:
        with self._lock:
            self.records.append(r)
            if r.provider == "offline":
                self.used_offline = True
            spent = self.total_tokens_unlocked()
            if spent > self.budget:
                raise BudgetExceeded(spent, self.budget, self._per_agent_unlocked())

    def total_tokens_unlocked(self) -> int:
        return sum(r.prompt_tokens + r.output_tokens for r in self.records)

    def _per_agent_unlocked(self) -> dict[str, int]:
        per: dict[str, int] = defaultdict(int)
        for r in self.records:
            per[r.agent] += r.prompt_tokens + r.output_tokens
        return dict(per)

    @property
    def total_tokens(self) -> int:
        with self._lock:
            return self.total_tokens_unlocked()

    @property
    def per_agent(self) -> dict[str, int]:
        with self._lock:
            return self._per_agent_unlocked()

    @property
    def total_latency_ms(self) -> int:
        with self._lock:
            return sum(r.latency_ms for r in self.records)

    @property
    def cache_hits(self) -> int:
        with self._lock:
            return sum(1 for r in self.records if r.cache_hit)

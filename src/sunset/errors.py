"""Typed errors. Each one names a specific failure the product must not paper over."""

from __future__ import annotations


class SunsetError(Exception):
    """Base class for everything raised deliberately in this package."""


class CassetteMiss(SunsetError):
    """Replay mode was asked for a request hash that has no recorded response.

    This is a hard failure on purpose. A replay run that silently fell through
    to a live call would make the offline/CI story a lie.
    """


class BudgetExceeded(SunsetError):
    """A run crossed the token budget.

    We stop rather than truncate evidence to fit — truncating evidence to hit a
    round number is exactly how you manufacture a catastrophic error (spec §9.3).
    """

    def __init__(self, spent: int, budget: int, per_agent: dict[str, int]):
        self.spent = spent
        self.budget = budget
        self.per_agent = per_agent
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(per_agent.items()))
        super().__init__(
            f"token budget exceeded: {spent} > {budget} ({breakdown})"
        )


class CitationUnresolved(SunsetError):
    """A memo cited evidence that does not resolve to a real row.

    The whole product premise dies if a hallucinated citation reaches the UI, so
    this fails the feature loudly rather than degrading quietly.
    """


class ProviderConfigError(SunsetError):
    """The configured provider mode is unusable (e.g. live mode with no key)."""

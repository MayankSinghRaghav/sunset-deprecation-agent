"""The per-feature graph state. One LangGraph thread per feature
(thread_id = "{run_id}:{feature_id}") because the human interrupt and the
checkpoint resume are per-feature.

Only serialisable data lives here — the live AuditContext (connection, provider)
is passed through `config["configurable"]`, not the state, so a checkpoint can be
resumed in a fresh process with a fresh context.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def _take_last(a, b):
    return b if b is not None else a


class FeatureAuditState(TypedDict, total=False):
    feature_id: str
    run_id: str
    prefilter_verdict: str
    # the audit result, as plain dicts (serialisable)
    verdict: str
    secondary_action: str | None
    confidence: str
    applied_rules: list[str]
    reflection_passes: int
    memo_markdown: str | None
    dissent: str | None
    citation_clean: bool
    # trace grows as nodes run
    trace: Annotated[list[str], operator.add]
    # human review
    needs_review: bool
    human_override: dict[str, Any] | None
    status: str

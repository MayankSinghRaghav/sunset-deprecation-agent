"""Deterministic dataset generator.

Reads the hand-written truth sheet and emits the evidence that ENCODES those
verdicts — usage, tickets, contracts, deal notes, dependency edges — as committed
fixtures. Byte-identical from `seed`, so anyone can reproduce the dataset without
an API key or network (the optional LLM prose pass is layered on separately in
prose.py and never changes the structural signal).

Run:  uv run python -m datagen.generate --i-understand-this-changes-the-golden-set
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from datagen import fixtures_io as fio
from datagen.traps import Account, generate_usage
from datagen.truthsheet import load_truth
from datagen.world import (
    CONTRACT_OBLIGATIONS,
    DATASET_VERSION,
    DEAL_CITATIONS,
    DEPENDENCIES,
    FEATURE_META,
    MAINTENANCE_USD,
    MID_MARKET,
    REPLACEMENTS,
    WHALES,
    WINDOW_END,
    WINDOW_START,
)

SEED = 1337


# ===========================================================================
# Accounts
# ===========================================================================

_SMB_PREFIXES = [
    "Pinehill", "Oakmont", "Cedar", "Maple", "Birchwood", "Willow", "Ashford",
    "Fernbank", "Elmwood", "Hollow", "Ridgeline", "Brookside", "Clearwater",
    "Stonegate", "Meadow", "Foxglen", "Dovetail", "Highpoint", "Lakeshore",
    "Sandpiper", "Copperfield", "Thistle", "Marigold", "Juniper", "Sable",
    "Verdant", "Kestrel", "Ironwood", "Amberly", "Nightjar", "Bramble",
    "Coralpoint", "Dunmore", "Everglade", "Frostwood", "Gale", "Heron",
    "Indigo", "Jasper", "Kingfisher", "Larch", "Mistral", "Nutmeg", "Opaline",
    "Pemberton",
]
_SMB_SUFFIXES = ["Systems", "Labs", "Group", "Co", "Digital", "Works", "Partners"]
_INDUSTRIES = [
    "retail", "technology", "healthcare", "manufacturing", "education",
    "media", "logistics", "insurance", "hospitality", "energy",
]


def build_accounts(rng: random.Random) -> list[Account]:
    accts: list[Account] = []
    for aid, _name, _ind, arr in WHALES:
        accts.append(Account(aid, "whale", arr))
    for aid, _name, _ind, arr in MID_MARKET:
        accts.append(Account(aid, "mid_market", arr))
    for i in range(45):
        aid = f"a{16 + i:02d}"
        arr = rng.randint(6_000, 40_000)
        accts.append(Account(aid, "smb", arr))
    return accts


def account_rows(rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    base_sign = date(2021, 1, 1)
    for aid, name, ind, arr in WHALES:
        rows.append(_acct_row(aid, name, "whale", arr, ind, base_sign, rng))
    for aid, name, ind, arr in MID_MARKET:
        rows.append(_acct_row(aid, name, "mid_market", arr, ind, base_sign, rng))
    for i in range(45):
        aid = f"a{16 + i:02d}"
        name = f"{_SMB_PREFIXES[i]} {_SMB_SUFFIXES[i % len(_SMB_SUFFIXES)]}"
        ind = _INDUSTRIES[i % len(_INDUSTRIES)]
        arr = rng.randint(6_000, 40_000)
        rows.append(_acct_row(aid, name, "smb", arr, ind, base_sign, rng))
    return rows


def _acct_row(aid, name, band, arr, ind, base_sign, rng):
    signed = base_sign + timedelta(days=rng.randint(0, 1500))
    seg = {"whale": "enterprise", "mid_market": "mid_market", "smb": "smb"}[band]
    return dict(
        id=aid, name=name, arr_band=band, arr_usd=arr, segment=seg,
        industry=ind, signed_at=signed.isoformat(),
    )


# ===========================================================================
# Features + dependencies
# ===========================================================================


def feature_rows(truth) -> list[dict]:
    rows = []
    launch_base = date(2019, 1, 1)
    for i, t in enumerate(truth):
        meta = FEATURE_META[t.feature_id]
        launched = launch_base + timedelta(days=i * 37)
        rows.append(dict(
            id=t.feature_id,
            name=t.feature_name,
            description=meta["desc"],
            area=meta["area"],
            launched_at=launched.isoformat(),
            maintenance_cost_band=meta["cost"],
            annual_maintenance_usd=MAINTENANCE_USD[meta["cost"]],
            replacement_feature_id=REPLACEMENTS.get(t.feature_id),
        ))
    return rows


def dependency_rows() -> list[dict]:
    return [
        dict(from_feature_id=f, to_feature_id=t, kind=k)
        for (f, t, k) in DEPENDENCIES
    ]


# ===========================================================================
# Contracts + clauses
# ===========================================================================

_FILLER_CLAUSES = [
    ("2.1 Term", "This Agreement commences on the Effective Date and continues for the Initial Term unless terminated earlier in accordance with its provisions."),
    ("3.4 Fees", "The Customer shall pay the fees set out in the applicable Order Form within thirty (30) days of invoice."),
    ("12.1 Limitation of Liability", "Neither party's aggregate liability shall exceed the fees paid in the twelve months preceding the claim."),
    ("10.2 Support", "Provider shall provide support in accordance with the support policy referenced in the Order Form."),
    ("14.3 Governing Law", "This Agreement shall be governed by the laws of the jurisdiction specified in the Order Form."),
]


@dataclass
class ClauseMap:
    """Kept in the generator only. NEVER written to an app-visible column."""
    clause_id: str
    feature_id: str
    status: str


def contract_rows_and_clauses(rng: random.Random):
    contracts: list[dict] = []
    clauses: list[dict] = []
    clause_map: list[ClauseMap] = []

    # which accounts have contracts: all whales + mid-market accounts that appear
    # in the obligations, deduped and capped at 12.
    obligated_accts = [o[0] for o in CONTRACT_OBLIGATIONS]
    accts = []
    for aid, *_ in WHALES:
        accts.append(aid)
    for aid, *_ in MID_MARKET:
        if aid in obligated_accts and aid not in accts:
            accts.append(aid)
    for aid, *_ in MID_MARKET:
        if len(accts) >= 12:
            break
        if aid not in accts:
            accts.append(aid)
    accts = accts[:12]

    cidx = 0
    for aid in accts:
        cid = f"c{cidx + 1:02d}"
        cidx += 1
        eff = date(2023, 1, 1) + timedelta(days=rng.randint(0, 400))
        exp = eff + timedelta(days=365 * 3)
        contracts.append(dict(
            id=cid, account_id=aid,
            title=f"Master Services Agreement — {aid}",
            effective_from=eff.isoformat(), expires_at=exp.isoformat(),
        ))
        sect = 0
        # obligation clauses for this account
        for (o_acct, fid, status, section, text) in CONTRACT_OBLIGATIONS:
            if o_acct != aid:
                continue
            clid = f"{cid}_s{sect}"
            sect += 1
            clauses.append(dict(id=clid, contract_id=cid, section=section, text=text))
            clause_map.append(ClauseMap(clid, fid, status))
        # filler clauses (deterministic subset)
        n_filler = 2 + (cidx % 3)
        picks = rng.sample(_FILLER_CLAUSES, k=min(n_filler, len(_FILLER_CLAUSES)))
        for (section, text) in picks:
            clid = f"{cid}_s{sect}"
            sect += 1
            clauses.append(dict(id=clid, contract_id=cid, section=section, text=text))
    return contracts, clauses, clause_map


# ===========================================================================
# Deal notes
# ===========================================================================

_COMPETITORS = ["Northgate", "Solaris", "Quorum", "Brightline", "Axiom", "Vantage"]

_TRAP7_WON_TEMPLATES = {
    "f37": "Security and compliance were the gating criteria. The evaluation team called out our compliance certifications center and the breadth of published attestations as the reason they were comfortable moving forward.",
    "f38": "The buyer needed to present the platform under their own brand to their downstream customers. Our white-label branding — custom domain, logos, and colours — was the deciding factor over {competitor}.",
    "f39": "A hard regulatory requirement meant a cloud-only vendor was a non-starter. Our on-premises deployment option is why we beat {competitor} in the final round.",
    "f40": "Their security review stalled every other vendor. Being able to hand over a SOC 2 evidence dashboard with the audit artefacts pre-assembled closed the deal.",
}

_GENERIC_WON = [
    "Straightforward competitive win. The team liked the reporting dashboard and the search experience in the demo.",
    "Expansion of an existing relationship; the Slack integration and API access were table stakes and we met them.",
    "Won on total cost of ownership. Product depth was adequate; procurement drove the decision.",
    "Champion-led deal. The dashboards resonated with the exec sponsor.",
    "Displaced an incumbent spreadsheet workflow. Ease of onboarding won it.",
]

_LOST = [
    "Lost to {competitor}. Prospect wanted deeper native analytics than we offer today.",
    "No decision — budget was pulled mid-cycle.",
    "Lost on price against {competitor}.",
    "Lost to an in-house build; they had spare engineering capacity.",
    "Prospect required a data-residency guarantee in a region we do not yet cover.",
    "Lost to {competitor} on integrations breadth.",
]


def deal_note_rows(accounts: list[Account], rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    acct_ids = sorted(a.id for a in accounts)
    n = 0

    # trap-7 won deals (the citations that make sales-criticality detectable)
    for fid, count in DEAL_CITATIONS.items():
        for _ in range(count):
            aid = rng.choice(acct_ids)
            comp = rng.choice(_COMPETITORS)
            body = _TRAP7_WON_TEMPLATES[fid].format(competitor=comp)
            closed = WINDOW_START + timedelta(days=rng.randint(0, 690))
            rows.append(dict(
                id=f"d{n + 1:03d}", account_id=aid, outcome="won",
                closed_at=closed.isoformat(), body=body,
            ))
            n += 1

    # generic won deals to reach 40 won
    while sum(1 for r in rows if r["outcome"] == "won") < 40:
        aid = rng.choice(acct_ids)
        body = rng.choice(_GENERIC_WON)
        closed = WINDOW_START + timedelta(days=rng.randint(0, 690))
        rows.append(dict(
            id=f"d{n + 1:03d}", account_id=aid, outcome="won",
            closed_at=closed.isoformat(), body=body,
        ))
        n += 1

    # 25 lost deals
    for _ in range(25):
        aid = rng.choice(acct_ids)
        body = rng.choice(_LOST).format(competitor=rng.choice(_COMPETITORS))
        closed = WINDOW_START + timedelta(days=rng.randint(0, 690))
        rows.append(dict(
            id=f"d{n + 1:03d}", account_id=aid, outcome="lost",
            closed_at=closed.isoformat(), body=body,
        ))
        n += 1

    rows.sort(key=lambda r: r["id"])
    return rows


# ===========================================================================
# Support tickets
# ===========================================================================

_DEFECT_SUBJECTS = [
    "{name} stopped working", "{name} not syncing anymore", "Errors from {name}",
    "{name} broken since the update", "{name} keeps failing",
]
_DEFECT_BODIES = [
    "Since around the start of October {name} has stopped working. We have tried reconnecting several times and it fails every time with the same error.",
    "{name} used to work fine but now every attempt errors out. This is the third ticket we have filed — can someone please look?",
    "We rely on {name} and it has been failing for weeks. Repeated retries do not help; it just times out.",
    "{name} is throwing errors on every run since the last change on your side. We need this fixed, not removed.",
]
_REQUEST_SUBJECTS = [
    "Feature request: {name}", "Can {name} also support…", "Please improve {name}",
    "Would love an addition to {name}",
]
_REQUEST_BODIES = [
    "We use {name} constantly and would love if it also supported threaded replies. Not urgent, just a nice-to-have.",
    "Big fan of {name}. Any chance you could add per-team configuration? Happy to beta test.",
    "{name} is great — could you add an export option? It would save us a lot of manual work.",
]
_COMPLAINT_SUBJECTS = [
    "Confusing behaviour in {name}", "{name} permissions are hard to reason about",
    "Edge case in {name}",
]
_COMPLAINT_BODIES = [
    "{name} is powerful but the edge cases around inherited permissions are confusing. We hit a surprising case this week — not blocking, but worth a look.",
    "Love that {name} exists, but configuring it for a large team is fiddly. Could the docs be clearer?",
    "A specific rule combination in {name} behaves unexpectedly. Workaround is fine for now.",
]
_NEUTRAL_SUBJECTS = [
    "Question about {name}", "How do I use {name}?", "{name} onboarding help",
]
_NEUTRAL_BODIES = [
    "New to {name} — is there a getting-started guide? Thanks!",
    "Quick question on {name}: how do I share a saved view with a colleague?",
    "Trying to understand what {name} does. Any docs?",
]


def _ticket(n, aid, fid, when, subject, body, resolution):
    return dict(
        id=f"t{n:04d}", account_id=aid, feature_id_guess=fid,
        created_at=when.isoformat() + "T12:00:00+00:00",
        subject=subject, body=body, resolution=resolution,
    )


def support_ticket_rows(truth, accounts, rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    acct_ids = sorted(a.id for a in accounts)
    tclass = {t.feature_id: t.trap_class for t in truth}
    fname = {t.feature_id: t.feature_name for t in truth}
    n = 0
    from datagen.world import BREAK_DATE

    def add(fid, when, subj_pool, body_pool, resolution):
        nonlocal n
        n += 1
        aid = rng.choice(acct_ids)
        nm = fname[fid]
        subj = rng.choice(subj_pool).format(name=nm)
        body = rng.choice(body_pool).format(name=nm)
        rows.append(_ticket(n, aid, fid, when, subj, body, resolution))

    # trap-4: dense defect clusters AFTER the break date (the temporal signal)
    for fid, tc in tclass.items():
        if tc != "broken_not_unwanted":
            continue
        for _ in range(rng.randint(34, 42)):
            offset = rng.randint(0, (WINDOW_END - BREAK_DATE).days)
            when = BREAK_DATE + timedelta(days=offset)
            add(fid, when, _DEFECT_SUBJECTS, _DEFECT_BODIES, "investigating")

    # distractor f11 (RBAC keep): complaints spread across the whole window —
    # engagement, not defect, and not clustered after a drop.
    for _ in range(rng.randint(40, 48)):
        when = WINDOW_START + timedelta(days=rng.randint(0, (WINDOW_END - WINDOW_START).days))
        add("f11", when, _COMPLAINT_SUBJECTS, _COMPLAINT_BODIES, "answered")

    # distractor f12 (Slack keep): feature requests — latent demand.
    for _ in range(rng.randint(30, 38)):
        when = WINDOW_START + timedelta(days=rng.randint(0, (WINDOW_END - WINDOW_START).days))
        add("f12", when, _REQUEST_SUBJECTS, _REQUEST_BODIES, "logged")

    # a few tickets on contract-bound features (realistic, low volume)
    for fid, tc in tclass.items():
        if tc != "contract_bound":
            continue
        for _ in range(rng.randint(2, 5)):
            when = WINDOW_START + timedelta(days=rng.randint(0, (WINDOW_END - WINDOW_START).days))
            add(fid, when, _NEUTRAL_SUBJECTS, _NEUTRAL_BODIES, "answered")

    # scatter neutral tickets across all features until we reach ~800
    all_fids = sorted(tclass)
    while n < 800:
        fid = rng.choice(all_fids)
        when = WINDOW_START + timedelta(days=rng.randint(0, (WINDOW_END - WINDOW_START).days))
        add(fid, when, _NEUTRAL_SUBJECTS, _NEUTRAL_BODIES, "answered")

    rows.sort(key=lambda r: r["id"])
    return rows


# ===========================================================================
# Orchestration
# ===========================================================================


def build_all():
    truth = load_truth()
    py_rng = random.Random(SEED)

    accounts = build_accounts(py_rng)

    accts = account_rows(random.Random(SEED + 1))
    feats = feature_rows(truth)
    deps = dependency_rows()
    contracts, clauses, clause_map = contract_rows_and_clauses(random.Random(SEED + 2))
    deals = deal_note_rows(accounts, random.Random(SEED + 3))
    tickets = support_ticket_rows(truth, accounts, random.Random(SEED + 4))

    # usage: one independent numpy Generator per feature
    usage: list = []
    for i, t in enumerate(sorted(truth, key=lambda x: x.feature_id)):
        g = np.random.default_rng(SEED * 1000 + i)
        usage.extend(generate_usage(t.feature_id, t.trap_class, accounts, g))
    usage.sort(key=lambda u: (u.feature_id, u.account_id, u.day, u.actor_type))

    return dict(
        accounts=accts, features=feats, dependencies=deps, contracts=contracts,
        clauses=clauses, clause_map=clause_map, deals=deals, tickets=tickets,
        usage=usage,
    )


def main():
    ap = argparse.ArgumentParser(description="Regenerate the Sunset dataset fixtures.")
    ap.add_argument(
        "--i-understand-this-changes-the-golden-set",
        action="store_true",
        dest="confirm",
        help="Required. Regenerating changes committed fixtures.",
    )
    ap.add_argument("--check", action="store_true",
                    help="Generate in-memory and print counts without writing files.")
    args = ap.parse_args()

    data = build_all()
    counts = {k: len(v) for k, v in data.items() if k != "clause_map"}
    print("Generated:", json.dumps(counts, indent=2))

    if args.check:
        return
    if not args.confirm:
        raise SystemExit(
            "Refusing to write fixtures without "
            "--i-understand-this-changes-the-golden-set"
        )
    fio.write_fixtures(data, seed=SEED, dataset_version=DATASET_VERSION)
    print("Fixtures written to db/fixtures/")


if __name__ == "__main__":
    main()

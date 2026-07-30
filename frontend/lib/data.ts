// Types + mock data + a typed client for the FastAPI backend.
// The UI renders standalone from MOCK; if NEXT_PUBLIC_API_BASE is set the client
// hits the real endpoints and falls back to MOCK on error, so the design is
// always viewable without a running backend.

export type Verdict = "KILL" | "MIGRATE" | "KEEP" | "FIX" | "ESCALATE";
export type Confidence = "high" | "medium" | "low";

export interface FeatureRow {
  id: string;
  name: string;
  area: string;
  verdict: Verdict;
  reclassify?: boolean;
  confidence: Confidence;
  annual_cost: number;
  risk_accounts: string | null;
  reviewed: string;
}

export interface Claim {
  who: "Usage" | "Contract" | "Support" | "Revenue";
  amber?: boolean;
  text: string;
  citation: { id: string; source: string; quote: string };
}
export interface AtRisk { name: string; why: string; arr: string; }
export interface Memo {
  id: string;
  name: string;
  area: string;
  verdict: Verdict;
  reclassify?: boolean;
  confidence: Confidence;
  headline: string;
  annual_cost: number;
  revenue_exposure?: string;
  claims: Claim[];
  timeline: { when: string; what: string; warn?: boolean }[];
  recommendation: { eyebrow: string; heading: string; body: string };
  at_risk: AtRisk[];
  migration: string[] | null;
  dissent: string;
  applied_rule: string;
}

export const VERDICT_STYLE: Record<Verdict, { label: string; kind: "safe" | "neutral" | "risk" | "escalate" }> = {
  KEEP: { label: "Keep", kind: "safe" },
  KILL: { label: "Kill", kind: "neutral" },
  MIGRATE: { label: "Migrate", kind: "risk" },
  ESCALATE: { label: "Escalate", kind: "escalate" },
  FIX: { label: "Fix", kind: "neutral" },
};

export const CATALOGUE: FeatureRow[] = [
  { id: "f08", name: "Dashboard v2", area: "Reporting", verdict: "KEEP", confidence: "high", annual_cost: 260000, risk_accounts: null, reviewed: "2d ago" },
  { id: "f23", name: "Multi-Currency Billing", area: "Billing", verdict: "MIGRATE", confidence: "medium", annual_cost: 260000, risk_accounts: "3 whale accounts", reviewed: "2d ago" },
  { id: "f13", name: "Audit Log Export", area: "Security", verdict: "ESCALATE", confidence: "high", annual_cost: 120000, risk_accounts: "2 accounts · contract", reviewed: "2d ago" },
  { id: "f25", name: "Salesforce Sync", area: "Integrations", verdict: "FIX", confidence: "medium", annual_cost: 260000, risk_accounts: null, reviewed: "2d ago" },
  { id: "f16", name: "Scheduled PDF Reports", area: "Reporting", verdict: "MIGRATE", confidence: "medium", annual_cost: 120000, risk_accounts: "Harbor Insurance", reviewed: "2d ago" },
  { id: "f33", name: "Status Page Widget", area: "Collaboration", verdict: "KILL", confidence: "high", annual_cost: 40000, risk_accounts: null, reviewed: "2d ago" },
  { id: "f37", name: "Compliance Certifications Center", area: "Security", verdict: "KEEP", reclassify: true, confidence: "medium", annual_cost: 120000, risk_accounts: null, reviewed: "2d ago" },
  { id: "f01", name: "Legacy Dashboard v1", area: "Reporting", verdict: "KILL", confidence: "high", annual_cost: 120000, risk_accounts: null, reviewed: "2d ago" },
  { id: "f30", name: "Tax Document Generator", area: "Billing", verdict: "KEEP", confidence: "high", annual_cost: 120000, risk_accounts: null, reviewed: "2d ago" },
  { id: "f20", name: "Rate Limiter Service", area: "Developer", verdict: "MIGRATE", confidence: "medium", annual_cost: 40000, risk_accounts: "depended on by REST API", reviewed: "2d ago" },
  { id: "f14", name: "Data Residency Controls", area: "Security", verdict: "ESCALATE", confidence: "high", annual_cost: 260000, risk_accounts: "Meridian Health · SLA", reviewed: "2d ago" },
  { id: "f02", name: "Flash Uploader", area: "Data", verdict: "KILL", confidence: "high", annual_cost: 40000, risk_accounts: null, reviewed: "2d ago" },
  { id: "f26", name: "Mobile Push Notifications", area: "Mobile", verdict: "FIX", confidence: "high", annual_cost: 120000, risk_accounts: null, reviewed: "2d ago" },
  { id: "f39", name: "On-Prem Deployment Option", area: "Security", verdict: "KEEP", reclassify: true, confidence: "low", annual_cost: 260000, risk_accounts: null, reviewed: "2d ago" },
];

export const MEMO: Memo = {
  id: "f23", name: "Multi-Currency Billing", area: "Billing", verdict: "MIGRATE",
  confidence: "medium",
  headline: "Remove Multi-Currency Billing — after moving three accounts.",
  annual_cost: 260000, revenue_exposure: "$2.21M ARR",
  claims: [
    { who: "Usage", text: "Only three accounts touch this feature — well under one percent of the base — but their usage is steady, not declining.",
      citation: { id: "ev_9f2a11c4", source: "usage_daily", quote: "26,879 human events across 3 accounts, all whale-band" } },
    { who: "Revenue", amber: true, text: "Those three accounts are the platform's largest by ARR. Raw user count says remove it; revenue concentration says migrate them first.",
      citation: { id: "ev_2c7d0b83", source: "accounts", quote: "Vertex Financial, Meridian Health, Atlas Global — 40% of total ARR" } },
    { who: "Contract", text: "No signed obligation attaches to this capability. Removal is a product decision, not a legal one — provided the accounts are migrated cleanly.",
      citation: { id: "status", source: "contract_clauses", quote: "clear · no matching clause above threshold" } },
    { who: "Support", text: "Eleven tickets over the window, none indicating a defect. A feature that works and is quietly used by a few important customers.",
      citation: { id: "ev_51ba77e2", source: "support_tickets", quote: "11 tickets · 0 defect signals · sentiment neutral" } },
  ],
  timeline: [
    { when: "18 months ago", what: "Adopted by three enterprise accounts during multi-region rollout." },
    { when: "Trailing year", what: "Usage flat. No new adopters. No churn among the three." },
    { when: "This quarter", what: "Flagged for review — maintenance cost high, adoption negligible.", warn: true },
  ],
  recommendation: {
    eyebrow: "Recommendation",
    heading: "Migrate the three accounts to REST API bulk endpoints, then remove.",
    body: "The feature earns its place through revenue, not usage. Removing it outright would put $2.21M of ARR at risk across three named accounts. A staged migration retires the maintenance burden without touching the renewal.",
  },
  at_risk: [
    { name: "Vertex Financial", why: "whale · concentrated usage", arr: "$880K ARR" },
    { name: "Meridian Health Systems", why: "whale · concentrated usage", arr: "$720K ARR" },
    { name: "Atlas Global Logistics", why: "whale · concentrated usage", arr: "$610K ARR" },
  ],
  migration: [
    "Confirm REST API bulk endpoints cover each account's currency configuration.",
    "Migrate Vertex, Meridian and Atlas in a supervised window; verify invoice parity.",
    "Deprecate on the next major version once all three confirm cutover.",
  ],
  dissent: "If the replacement fully covers each account today, this is a clean removal — not a migration. Before committing engineering effort, verify the REST bulk endpoints already handle every currency rule these three accounts rely on. If they do, the migration plan is overhead and the feature can simply be retired.",
  applied_rule: "R3 · revenue cap",
};

export const TRAPS: { name: string; slug: string; base: number; agent: number }[] = [
  { name: "Obvious kill", slug: "none_kill", base: 7, agent: 6 },
  { name: "Obvious keep", slug: "none_keep", base: 4, agent: 5 },
  { name: "Contract-bound", slug: "trap 1", base: 1, agent: 4 },
  { name: "Hidden dependency", slug: "trap 2", base: 0, agent: 4 },
  { name: "Segment-concentrated", slug: "trap 3", base: 0, agent: 4 },
  { name: "Broken, not unwanted", slug: "trap 4", base: 0, agent: 4 },
  { name: "Seasonal", slug: "trap 5", base: 1, agent: 4 },
  { name: "Phantom usage", slug: "trap 6", base: 0, agent: 4 },
  { name: "Sales-critical", slug: "trap 7", base: 0, agent: 3 },
];

export const EXPOSURE = {
  account: { name: "Vertex Financial", band: "Whale", arr: "$880K", industry: "Financial services", since: "2021" },
  features_at_risk: 4,
  revenue_at_stake: "$880K",
  rows: [
    { name: "Multi-Currency Billing", verdict: "MIGRATE" as Verdict, action: "Migrate to REST bulk endpoints first", cost: 260000 },
    { name: "Audit Log Export", verdict: "ESCALATE" as Verdict, action: "Legal review — obligated by MSA", cost: 120000 },
    { name: "Data Residency Controls", verdict: "ESCALATE" as Verdict, action: "Legal review — SLA data-region clause", cost: 260000 },
    { name: "Dedicated Sandbox Environments", verdict: "MIGRATE" as Verdict, action: "Provision replacement environment", cost: 260000 },
  ],
};

export const SCORECARD = {
  baseline: { accuracy: 0.325, correct: 13, total: 40, catastrophic: 2 },
  agent: { offline: true, catastrophic: 0, citations: 1.0, escalation_precision: 1.0 },
  cost: { tokens: "43.5K", budget: "150K", latency: "1.4s", prefilter: "12%" },
};

export function money(n: number): string {
  return n >= 1000 ? `$${Math.round(n / 1000)}K` : `$${n}`;
}

// --- optional live client -------------------------------------------------
const API = process.env.NEXT_PUBLIC_API_BASE;
export async function fetchScorecard() {
  if (!API) return null;
  try {
    const r = await fetch(`${API}/eval/scorecard`, { cache: "no-store" });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

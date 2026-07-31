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

export const MEMOS: Record<string, Memo> = {
  f23: {
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
  },
  f13: {
    id: "f13", name: "Audit Log Export", area: "Security", verdict: "ESCALATE",
    confidence: "high",
    headline: "Escalate Audit Log Export to Legal — Contract Obligation Found.",
    annual_cost: 120000, revenue_exposure: "$1.045M ARR",
    claims: [
      { who: "Usage", text: "Very low usage over the past 90 days. Less than 5 requests total, representing minimal customer interaction.",
        citation: { id: "ev_1298af7d", source: "usage_daily", quote: "4 events from 2 accounts (Vertex Financial, Northwind Retail)" } },
      { who: "Contract", amber: true, text: "Obligated under Master Services Agreement for Vertex and Northwind. Section 8.4 mandates 'Exportable machine-readable event logs on demand'.",
        citation: { id: "status", source: "contract_clauses", quote: "MSA Section 8.4 compliance required · penalty for breach: termination" } },
      { who: "Support", text: "No support tickets or defects reported over the last year.",
        citation: { id: "ev_873bf911", source: "support_tickets", quote: "0 tickets · sentiment N/A" } },
    ],
    timeline: [
      { when: "24 months ago", what: "Feature added to satisfy Enterprise security compliance checklist." },
      { when: "12 months ago", what: "Vertex and Northwind MSAs renewed containing Section 8.4 export requirements." },
      { when: "This quarter", what: "Usage falls below 1%. Flagged for standard deprecation review.", warn: true },
    ],
    recommendation: {
      eyebrow: "Recommendation",
      heading: "Halt deprecation. Escalate to legal & customer success for contract renegotiation.",
      body: "Removing this feature violates MSA compliance commitments for Vertex Financial and Northwind Retail, risking immediate breach of contract and up to $1.045M in ARR. We must escalate to renegotiate the terms or maintain the codebase.",
    },
    at_risk: [
      { name: "Vertex Financial", why: "SLA / MSA explicit clause", arr: "$880K ARR" },
      { name: "Northwind Retail", why: "MSA custom compliance rider", arr: "$165K ARR" },
    ],
    migration: null,
    dissent: "Our standard REST API already provides raw audit endpoints. We should verify if our legal counsel can argue that providing REST endpoints satisfies Section 8.4, allowing us to retire the legacy Web UI exporter without triggering a breach.",
    applied_rule: "C1 · contract lock",
  },
  f25: {
    id: "f25", name: "Salesforce Sync", area: "Integrations", verdict: "FIX",
    confidence: "medium",
    headline: "Do Not Deprecate Salesforce Sync — Usage Dropped Due to Bug.",
    annual_cost: 260000, revenue_exposure: "$165K ARR",
    claims: [
      { who: "Usage", text: "Usage collapsed by 95% following the v4.8 core engine release three weeks ago. Looks dead but is actually broken.",
        citation: { id: "ev_55a2b1c3", source: "usage_daily", quote: "Event count dropped from 15,000 daily to 250 daily" } },
      { who: "Support", amber: true, text: "Spike of 18 high-priority tickets complaining about synchronization errors and OAuth connection resets.",
        citation: { id: "ev_392f811a", source: "support_tickets", quote: "18 tickets · OAuth state mismatch · sentiment highly negative" } },
      { who: "Revenue", text: "Primarily used by mid-market accounts. Northwind Retail renewal is contingent on functioning sync.",
        citation: { id: "ev_448fa392", source: "crm_deal_notes", quote: "Northwind CS note: Salesforce sync stability is key blocker for renewal" } },
    ],
    timeline: [
      { when: "4 weeks ago", what: "V4.8 core engine upgrade shipped." },
      { when: "3 weeks ago", what: "Usage collapses. Support tickets spike.", warn: true },
      { when: "This week", what: "Telemetry flags Salesforce Sync as deprecation candidate due to low usage." },
    ],
    recommendation: {
      eyebrow: "Recommendation",
      heading: "Assign engineering resources to repair OAuth state management, keep feature.",
      body: "Low usage is a false signal caused by a critical bug, not lack of user interest (Trap 4). Deprecating the integration would break core workflows for our mid-market customers. Assign a fix sprint immediately.",
    },
    at_risk: [
      { name: "Northwind Retail", why: "concentrated dependency", arr: "$165K ARR" },
    ],
    migration: [
      "Rollback OAuth token refresh changes introduced in v4.8.",
      "Deploy hotfix and monitor customer oauth connection rates.",
      "Verify ticket count returns to zero baseline.",
    ],
    dissent: "If the cost of maintaining this legacy custom Salesforce integration is $260K/year, it might be more economical to retire it anyway and push users toward our standardized integration on the Salesforce AppExchange.",
    applied_rule: "S2 · defect spike override",
  },
  f30: {
    id: "f30", name: "Tax Document Generator", area: "Billing", verdict: "KEEP",
    confidence: "high",
    headline: "Keep Tax Document Generator — Usage is Seasonal.",
    annual_cost: 120000, revenue_exposure: "$0 ARR",
    claims: [
      { who: "Usage", text: "Dormant for 10 months of the year, but shows massive spikes in Q1. This is a seasonal compliance requirement.",
        citation: { id: "ev_77a299d2", source: "usage_daily_24mo", quote: "Usage peaks at 42,000 events in Jan/Feb; drops to <50 events in summer" } },
      { who: "Contract", text: "No custom contracts, but compliance standards require availability of historical forms.",
        citation: { id: "status", source: "compliance_checks", quote: "SOC2 Audit compliance check passed" } },
    ],
    timeline: [
      { when: "2 years ago", what: "Feature built to automate tax document generation." },
      { when: "Last Jan-Feb", what: "Highest seasonal peak with 42,000 downloads." },
      { when: "Last summer", what: "Zero usage recorded. Flagged by automated cron as inactive.", warn: true },
    ],
    recommendation: {
      eyebrow: "Recommendation",
      heading: "Retain feature. Seasonal compliance functionality.",
      body: "The feature shows typical seasonality (Trap 5). While it looks dead for most of the year, it is vital during Q1 filing season. It must be kept to satisfy compliance rules and prevent customer panic in January.",
    },
    at_risk: [],
    migration: null,
    dissent: "We can offload this maintenance burden entirely by integrating a tax reporting widget like Stripe Tax. This would keep compliance intact while eliminating our custom tax rendering engine.",
    applied_rule: "U2 · seasonal peak override",
  },
  f33: {
    id: "f33", name: "Status Page Widget", area: "Collaboration", verdict: "KILL",
    confidence: "high",
    headline: "Deprecate Status Page Widget — Traffic is 100% Bots/QA.",
    annual_cost: 40000, revenue_exposure: "$0 ARR",
    claims: [
      { who: "Usage", amber: true, text: "High raw traffic count is a false signal. 99.8% of hits are automated uptime pings and QA test bots; human traffic is zero.",
        citation: { id: "ev_012e98a1", source: "usage_daily", quote: "12,400 bot events, 0 human actions over 90 days" } },
      { who: "Support", text: "Zero support tickets or customer queries in the past 12 months.",
        citation: { id: "ev_81b99ff1", source: "support_tickets", quote: "0 tickets · sentiment N/A" } },
    ],
    timeline: [
      { when: "3 years ago", what: "Status Page widget built for embed code." },
      { when: "12 months ago", what: "Customers migrated to native status page hosting; widget deprecated in docs." },
      { when: "This quarter", what: "Auditor flags traffic is purely automated health checks.", warn: true },
    ],
    recommendation: {
      eyebrow: "Recommendation",
      heading: "Kill legacy Status Page Widget. Re-route health checks.",
      body: "All usage is synthetic (Trap 6). Real customers do not interact with this widget anymore. Retire the hosting endpoint and save the $40K maintenance cost immediately.",
    },
    at_risk: [],
    migration: [
      "Send notifications to DNS administrators hosting legacy status pages.",
      "Retire the widget endpoint on public CDNs.",
      "Shut down VM nodes and update firewall rules.",
    ],
    dissent: "Verify if any developer clients are parsing the raw JSON output of the widget as an undocumented API. Shutting the endpoint down abruptly could trigger error warnings in client monitoring.",
    applied_rule: "U1 · human usage threshold",
  },
  f37: {
    id: "f37", name: "Compliance Certifications Center", area: "Security", verdict: "KEEP",
    reclassify: true,
    confidence: "medium",
    headline: "Retain Compliance Center — Dead in App, Critical in Sales.",
    annual_cost: 120000, revenue_exposure: "$450K pipeline",
    claims: [
      { who: "Usage", text: "Zero active users in the application over the past 6 months.",
        citation: { id: "ev_22a7f1c3", source: "usage_daily", quote: "0 human events, 0 sessions" } },
      { who: "Revenue", amber: true, text: "Highly referenced in active enterprise opportunities. Cited as a critical feature in 8 won deals and 4 active sales RFPs.",
        citation: { id: "ev_99e8c71b", source: "crm_deal_notes", quote: "SOC2/HIPAA assurance dashboard mentioned in 8 closed-won SFDC records" } },
    ],
    timeline: [
      { when: "12 months ago", what: "Security team launches static certificates page." },
      { when: "6 months ago", what: "Dynamic Center usage drops to zero as users bookmark static docs." },
      { when: "This month", what: "Flagged for removal due to zero usage.", warn: true },
    ],
    recommendation: {
      eyebrow: "Recommendation",
      heading: "Keep the Compliance Certifications Center, reclassify as sales collateral.",
      body: "The feature is load-bearing in sales cycles but dormant post-signup (Trap 7). PMs should stop active feature development, but keeping it visible is vital for security audits during the sale. Reclassify to sales collateral.",
    },
    at_risk: [],
    migration: null,
    dissent: "Keeping a non-functional or unmaintained dashboard in the app just for sales demos creates a bad post-sale user experience. We should replace the live dashboard with a high-fidelity screenshot link in our documentation and deprecate the backend code.",
    applied_rule: "R1 · sales-critical override",
  },
  f20: {
    id: "f20", name: "Rate Limiter Service", area: "Developer", verdict: "MIGRATE",
    confidence: "medium",
    headline: "Migrate Rate Limiter Service — Hidden dependency detected.",
    annual_cost: 40000,
    claims: [
      { who: "Usage", text: "Zero direct client calls to the dashboard or admin interface.",
        citation: { id: "ev_44f1c990", source: "usage_daily", quote: "0 direct human configuration changes" } },
      { who: "Usage", amber: true, text: "CRITICAL: The backend service is actively depended on by our public REST API gateway (Dashboard v2 dependency graph).",
        citation: { id: "ev_99f2c111", source: "dependency_edges", quote: "f08 (Dashboard v2) -> f20 (Rate Limiter Service) dependency edge" } },
    ],
    timeline: [
      { when: "2 years ago", what: "Rate Limiter built as a standalone service." },
      { when: "1 year ago", what: "Integrated into Dashboard v2 gateway." },
      { when: "This quarter", what: "Standalone admin UI usage falls to zero. Flagged as dead.", warn: true },
    ],
    recommendation: {
      eyebrow: "Recommendation",
      heading: "Migrate configurations to REST Gateway, then deprecate admin UI.",
      body: "The feature is a hidden dependency (Trap 2). Deleting it breaks Dashboard v2. We must migrate the rate limiting rules to the main API gateway and retire the standalone service.",
    },
    at_risk: [
      { name: "All API Clients", why: "dependency breakage", arr: "Global API traffic" },
    ],
    migration: [
      "Map rate limit configuration schemas to the API gateway configuration store.",
      "Conduct a rolling cutover to gateway-managed rate limits.",
      "Decommission the separate Rate Limiter VMs.",
    ],
    dissent: "If the Rate Limiter functions perfectly and has a small footprint, migrating it might introduce latency issues into our API gateway. The code can be left alone as is.",
    applied_rule: "D1 · hidden dependency lock",
  }
};

export const MEMO = MEMOS.f23;

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

export interface AccountExposure {
  account: { name: string; band: string; arr: string; industry: string; since: string };
  features_at_risk: number;
  revenue_at_stake: string;
  rows: { name: string; verdict: Verdict; action: string; cost: number }[];
}

export const EXPOSURES: Record<string, AccountExposure> = {
  acct_01: {
    account: { name: "Vertex Financial", band: "Whale", arr: "$880K", industry: "Financial services", since: "2021" },
    features_at_risk: 4,
    revenue_at_stake: "$880K",
    rows: [
      { name: "Multi-Currency Billing", verdict: "MIGRATE", action: "Migrate to REST bulk endpoints first", cost: 260000 },
      { name: "Audit Log Export", verdict: "ESCALATE", action: "Legal review — obligated by MSA", cost: 120000 },
      { name: "Data Residency Controls", verdict: "ESCALATE", action: "Legal review — SLA data-region clause", cost: 260000 },
      { name: "Dedicated Sandbox Environments", verdict: "MIGRATE", action: "Provision replacement environment", cost: 260000 },
    ],
  },
  acct_02: {
    account: { name: "Meridian Health", band: "Whale", arr: "$720K", industry: "Healthcare Systems", since: "2020" },
    features_at_risk: 3,
    revenue_at_stake: "$720K",
    rows: [
      { name: "Multi-Currency Billing", verdict: "MIGRATE", action: "Migrate to REST bulk endpoints first", cost: 260000 },
      { name: "Data Residency Controls", verdict: "ESCALATE", action: "Legal review — SLA data-region clause", cost: 260000 },
      { name: "Scheduled PDF Reports", verdict: "MIGRATE", action: "Migrate to Dashboard Email Subscriptions", cost: 120000 },
    ],
  },
  acct_03: {
    account: { name: "Northwind Retail", band: "Mid-market", arr: "$165K", industry: "E-Commerce Logistics", since: "2022" },
    features_at_risk: 2,
    revenue_at_stake: "$165K",
    rows: [
      { name: "Salesforce Sync", verdict: "FIX", action: "Repair OAuth oauth token bug immediately", cost: 260000 },
      { name: "Audit Log Export", verdict: "ESCALATE", action: "Legal review — MSA Compliance Section 8.4", cost: 120000 },
    ],
  },
  acct_04: {
    account: { name: "Harbor Insurance", band: "Mid-market", arr: "$132K", industry: "Insurance underwriters", since: "2023" },
    features_at_risk: 1,
    revenue_at_stake: "$132K",
    rows: [
      { name: "Scheduled PDF Reports", verdict: "MIGRATE", action: "Migrate to Dashboard Email Subscriptions", cost: 120000 },
    ],
  },
};

export const EXPOSURE = EXPOSURES.acct_01;

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

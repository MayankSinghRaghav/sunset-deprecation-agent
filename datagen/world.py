"""Fixed domain facts. Authored, not random.

Everything here is deliberately arranged so that each trap's *non-usage* evidence
(contracts, deal notes, dependency edges) lands on exactly the right features, and
on no others. The most load-bearing constraint is on dependency edges: precedence
rule 5 caps a feature at MIGRATE if it has an inbound edge from a KEEP feature, so
a keep->X edge is only ever allowed when X is a trap-2 (hidden_dependency) feature.
A stray keep->kill edge would silently rescue a feature that ground truth says to
kill, and the eval would quietly break.
"""

from __future__ import annotations

from datetime import date

# --- observation window -----------------------------------------------------
# 24 months (spec §4.2 says 18; we use 24 so trap-5 seasonality spans two full
# annual cycles and is honestly detectable rather than a single bump).
WINDOW_START = date(2024, 7, 1)
WINDOW_END = date(2026, 6, 30)

# Trap 4: the date the broken features stopped working (~15 months in).
BREAK_DATE = date(2025, 10, 1)

DATASET_VERSION = "v1"

# --- accounts ---------------------------------------------------------------
# 3 whales, 12 mid-market, 45 SMB (spec §4.2). Whales and larger mid-market get
# contracts; whales drive the trap-3 revenue concentration.

WHALES = [
    ("a01", "Vertex Financial", "financial_services", 880_000),
    ("a02", "Meridian Health Systems", "healthcare", 720_000),
    ("a03", "Atlas Global Logistics", "logistics", 610_000),
]

MID_MARKET = [
    ("a04", "Northwind Retail", "retail", 165_000),
    ("a05", "Cobalt Software", "technology", 148_000),
    ("a06", "Harbor Insurance", "insurance", 132_000),
    ("a07", "Sterling Manufacturing", "manufacturing", 121_000),
    ("a08", "Beacon Education", "education", 98_000),
    ("a09", "Cypress Media", "media", 92_000),
    ("a10", "Fulton Energy", "energy", 88_000),
    ("a11", "Riverside Hospitality", "hospitality", 74_000),
    ("a12", "Quill Publishing", "media", 69_000),
    ("a13", "Delta Freight", "logistics", 63_000),
    ("a14", "Ember Retail Group", "retail", 61_000),
    ("a15", "Larkspur Biotech", "healthcare", 58_000),
]

# SMB roster is generated procedurally in generate.py (a16..a60) so the file
# stays readable; only the accounts that anchor cross-references are named here.

# --- features ---------------------------------------------------------------
# description is app-visible and must read as a neutral product description. It is
# ALSO what the contract/revenue auditors embed to match capability language, so
# for trap-1 and trap-7 features the description deliberately states the capability
# in plain product terms (not a label — a genuine description).

FEATURE_META: dict[str, dict] = {
    "f01": dict(area="Reporting", cost="medium", desc="First-generation reporting dashboard; the original charts-and-tables view that predates the current dashboard."),
    "f02": dict(area="Data", cost="low", desc="Browser-plugin based file uploader for bulk attachments."),
    "f03": dict(area="Data", cost="low", desc="The original keyword search over records, using the legacy index."),
    "f04": dict(area="Collaboration", cost="low", desc="Delivers activity updates as an RSS feed subscribers can poll."),
    "f05": dict(area="Developer", cost="medium", desc="Legacy SOAP web-service endpoint for programmatic access to platform data."),
    "f06": dict(area="Mobile", cost="low", desc="Desktop notification widget that surfaced alerts outside the browser."),
    "f07": dict(area="Collaboration", cost="low", desc="Batch daily email summarising the previous day's activity."),
    "f08": dict(area="Reporting", cost="high", desc="The primary reporting dashboard: interactive charts, filters, and saved views used across the product."),
    "f09": dict(area="Data", cost="high", desc="Global search across every record type, powering primary navigation."),
    "f10": dict(area="Developer", cost="high", desc="The REST API: documented programmatic access to platform data and actions."),
    "f11": dict(area="Security", cost="high", desc="Role-based access control governing who can see and do what."),
    "f12": dict(area="Integrations", cost="high", desc="Two-way Slack integration for notifications and actions in channels."),
    "f13": dict(area="Security", cost="medium", desc="Exports a tamper-evident record of administrative and security actions for compliance retention."),
    "f14": dict(area="Security", cost="high", desc="Controls that keep customer data stored within a customer-designated geographic region."),
    "f15": dict(area="Security", cost="high", desc="SAML single sign-on: authenticate end users through the customer's own identity provider."),
    "f16": dict(area="Reporting", cost="medium", desc="Periodic delivery of formatted PDF report summaries on a schedule."),
    "f17": dict(area="Data", cost="medium", desc="Entity resolution service that de-duplicates and links records; used as a backing service."),
    "f18": dict(area="Automation", cost="medium", desc="Notification routing service that fans events out to delivery channels."),
    "f19": dict(area="Reporting", cost="medium", desc="Template rendering engine that turns report definitions into formatted output."),
    "f20": dict(area="Developer", cost="low", desc="Rate limiting service that enforces per-tenant request quotas."),
    "f21": dict(area="Reporting", cost="medium", desc="Custom SLA attainment reporting with negotiated thresholds per account."),
    "f22": dict(area="Data", cost="medium", desc="Bulk data import endpoint for large one-shot data loads during onboarding."),
    "f23": dict(area="Billing", cost="high", desc="Multi-currency billing and invoicing for accounts transacting in several currencies."),
    "f24": dict(area="Developer", cost="high", desc="Dedicated, isolated sandbox environments provisioned per enterprise account."),
    "f25": dict(area="Integrations", cost="high", desc="Two-way synchronisation of records with Salesforce."),
    "f26": dict(area="Mobile", cost="medium", desc="Push notifications to the mobile apps."),
    "f27": dict(area="Data", cost="medium", desc="Excel add-in that pulls live data into spreadsheets."),
    "f28": dict(area="Automation", cost="medium", desc="Outbound webhook delivery of platform events to customer endpoints."),
    "f29": dict(area="Billing", cost="medium", desc="Year-end financial close reporting used during the December-January close."),
    "f30": dict(area="Billing", cost="medium", desc="Generates tax documents; used heavily during the annual tax-filing season."),
    "f31": dict(area="Automation", cost="medium", desc="Open-enrollment benefit workflows run during the annual enrollment window."),
    "f32": dict(area="Automation", cost="medium", desc="Capacity and load planning for the run-up to the annual retail peak season."),
    "f33": dict(area="Collaboration", cost="low", desc="Embeddable public status-page widget showing service health."),
    "f34": dict(area="Automation", cost="low", desc="Legacy webhook healthcheck endpoint used to verify delivery."),
    "f35": dict(area="Developer", cost="medium", desc="Public API sandbox where anyone can try the API without an account."),
    "f36": dict(area="Collaboration", cost="low", desc="Embedded demo mode showcasing the product with seeded sample data."),
    "f37": dict(area="Security", cost="medium", desc="Compliance certifications center listing the platform's certifications and controls."),
    "f38": dict(area="Admin", cost="medium", desc="White-label branding: customer logos, colours, and custom domains."),
    "f39": dict(area="Security", cost="high", desc="On-premises deployment option for customers who cannot use the cloud."),
    "f40": dict(area="Security", cost="medium", desc="SOC 2 evidence dashboard collecting audit artefacts for security reviews."),
}

MAINTENANCE_USD = {"low": 40_000, "medium": 120_000, "high": 260_000}

# replacement_feature_id: drives the migration-plan rule (propose a plan only
# when a replacement exists; otherwise state the requirement and stop).
REPLACEMENTS = {
    "f01": "f08",
    "f03": "f09",
    "f05": "f10",
    "f07": "f12",
    "f16": "f08",
    "f21": "f08",
    "f22": "f10",
}

# --- dependency edges -------------------------------------------------------
# (from_feature, to_feature, kind) means "from depends on to". An inbound edge to
# a trap-2 feature FROM a keep feature is what precedence rule 5 keys on.
# Edges from KEEP features (f08,f09,f10,f11,f12) may ONLY target trap-2 features
# (f17,f18,f19,f20). See module docstring.
DEPENDENCIES = [
    # keep -> trap-2 (the load-bearing edges)
    ("f09", "f17", "reads_from"),   # Global Search reads from Entity Resolution
    ("f12", "f18", "calls"),        # Slack Integration calls Notification Router
    ("f08", "f19", "renders_in"),   # Dashboard v2 renders via Template Engine
    ("f10", "f20", "calls"),        # REST API calls Rate Limiter
    # non-keep -> various (safe: source is not a KEEP feature)
    ("f16", "f19", "renders_in"),   # Scheduled PDF also renders via Template Engine
    ("f25", "f10", "calls"),        # Salesforce Sync calls REST API
    ("f28", "f18", "calls"),        # Webhook Delivery calls Notification Router
    ("f13", "f10", "calls"),        # Audit Log Export calls REST API
    ("f26", "f18", "calls"),        # Mobile Push calls Notification Router
    ("f27", "f10", "calls"),        # Excel Add-in calls REST API
    ("f22", "f10", "calls"),        # Bulk Import calls REST API
    ("f21", "f19", "renders_in"),   # Custom SLA Reporting renders via Template Engine
    ("f29", "f19", "renders_in"),   # Year-End Close renders via Template Engine
    ("f30", "f19", "renders_in"),   # Tax Docs render via Template Engine
    ("f16", "f15", "auth_via"),     # Scheduled PDF auth via SAML
    ("f24", "f20", "calls"),        # Sandbox calls Rate Limiter
    ("f35", "f20", "calls"),        # Public API Sandbox calls Rate Limiter
    ("f04", "f18", "calls"),        # RSS Notifications calls Notification Router
    ("f07", "f18", "calls"),        # Email Digest calls Notification Router
    ("f31", "f19", "renders_in"),   # Open Enrollment renders via Template Engine
    ("f40", "f13", "reads_from"),   # SOC2 Dashboard reads from Audit Log Export
    ("f37", "f13", "reads_from"),   # Compliance Center reads from Audit Log Export
    ("f33", "f18", "calls"),        # Status Widget calls Notification Router
    ("f23", "f10", "calls"),        # Multi-currency billing calls REST API
    ("f34", "f18", "calls"),        # Webhook Healthcheck calls Notification Router
]

# --- contract obligations ---------------------------------------------------
# clause text uses CAPABILITY language, never a product feature name. The
# feature<->clause mapping lives here in the generator only; it is NEVER written
# to an app-visible column. The contract auditor must recover it semantically.
#
# tuple: (contract_account, feature_obligated, status, section, clause_text)
#   status: 'obligated' (hard) | 'possibly' (soft) | 'distractor' (red herring)
CONTRACT_OBLIGATIONS = [
    ("a01", "f13", "obligated", "8.2 Audit & Records",
     "Provider shall ensure the Customer retains, for the term of this Agreement and "
     "for seven years thereafter, the ability to export a complete, tamper-evident "
     "record of all administrative and security-relevant actions in a machine-readable format."),
    ("a04", "f13", "obligated", "11.4 Recordkeeping",
     "The Customer must at all times be able to produce an immutable log of privileged "
     "operations suitable for submission to an external auditor."),
    ("a02", "f14", "obligated", "5.1 Data Residency (SLA)",
     "All Customer Data, including backups, shall be stored and processed exclusively "
     "within the geographic region designated by the Customer at onboarding, and shall "
     "not be replicated outside that region without prior written consent."),
    ("a01", "f15", "obligated", "4.3 Authentication",
     "Provider shall permit the Customer to require that all end-user authentication be "
     "brokered through the Customer's own identity provider using an industry-standard "
     "federation protocol."),
    ("a03", "f15", "obligated", "6.2 Access Control",
     "End users shall authenticate exclusively via the Customer's designated single "
     "sign-on identity provider; local password authentication shall be disabled."),
    ("a05", "f15", "obligated", "3.9 Identity",
     "The Service must support delegated authentication to the Customer's federated "
     "identity system for all named users."),
    ("a06", "f16", "possibly", "9.1 Reporting",
     "Provider will make available periodic delivery of formatted summaries of account "
     "activity at a cadence to be mutually agreed."),
    # distractor: names a capability the SOAP endpoint relates to, but the
    # obligation is fully satisfied by the REST API, so the SOAP feature is safe
    # to remove. The contract auditor must NOT flag f05 as obligated.
    ("a07", "f05", "distractor", "7.7 Interfaces",
     "The Customer shall retain documented programmatic access to its data through a "
     "supported application programming interface."),
]

# --- deal-note citations (trap 7) -------------------------------------------
# Won deals cite these features as a reason the deal closed. The revenue auditor
# recovers this semantically from deal_notes.body.
#   feature -> number of won deals that cite it
DEAL_CITATIONS = {
    "f37": 6,  # Compliance Certifications Center
    "f38": 4,  # White-Label Branding
    "f39": 4,  # On-Prem Deployment Option
    "f40": 4,  # SOC2 Evidence Dashboard
}

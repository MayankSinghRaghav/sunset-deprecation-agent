import Link from "next/link";
import { CATALOGUE, money } from "@/lib/data";
import { VerdictBadge, Card, SectionLabel } from "@/components/ui";

const WRAP = "mx-auto max-w-[1180px] px-8";

export default function Home() {
  return (
    <div className={WRAP}>
      {/* hero */}
      <section className="pb-14 pt-24">
        <div className="eyebrow">Product Operations · Deprecation Review</div>
        <h1 className="mt-5 max-w-[15ch] text-[clamp(38px,6vw,64px)] tracking-[-0.02em]">
          Know which features can safely disappear.
        </h1>
        <p className="mt-6 max-w-[56ch] text-[19px] leading-[1.55] text-muted">
          Sunset assembles evidence from telemetry, contracts, support tickets and revenue signals into
          a case a product manager takes to a decision forum. The system builds the argument. Humans make
          the call.
        </p>
        <div className="mt-9 flex gap-3.5">
          <Link href="/catalogue" className="rounded-md border bg-surface px-4 py-2 text-[13px] font-medium transition-colors hover:border-faint">
            Open catalogue
          </Link>
          <Link href="/memo/f23" className="rounded-md px-4 py-2 text-[13px] font-medium text-muted transition-colors hover:text-text">
            See a decision memo →
          </Link>
        </div>
        <p className="mt-16 max-w-[46ch] border-t pt-5 font-display text-base italic text-muted">
          “Sunset assembles the case. A human signs the death warrant.”
        </p>
      </section>

      {/* workflow */}
      <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border bg-border md:grid-cols-4" style={{ boxShadow: "var(--shadow)" }}>
        {[
          ["01 · GATHER", "Evidence", "Telemetry, tickets, signed contracts and CRM deal notes — from a single system of record."],
          ["02 · READ", "Four auditors", "Usage, contract, support and revenue signals, each computed in code and interpreted in language."],
          ["03 · DECIDE", "Reconciler", "A deterministic policy layer applies precedence. It does not average, and it cannot kill a contract."],
          ["04 · PRESENT", "Memo", "A cited recommendation, the accounts at risk, and the strongest argument against itself."],
        ].map(([k, h, p]) => (
          <div key={k} className="bg-surface p-5">
            <div className="font-mono text-[11px] tracking-[0.1em] text-faint">{k}</div>
            <h4 className="mt-2.5 text-[17px]">{h}</h4>
            <p className="mt-1.5 text-[12.5px] leading-[1.45] text-muted">{p}</p>
          </div>
        ))}
      </div>

      {/* recent decisions */}
      <SectionLabel right={<Link href="/catalogue" className="font-mono text-xs text-muted hover:text-text">View catalogue →</Link>}>
        Recent decisions
      </SectionLabel>
      <Card className="overflow-hidden">
        <table className="w-full border-collapse">
          <thead>
            <tr>{["Feature", "Verdict", "Confidence", "Risk accounts", "Reviewed"].map((h) => (
              <th key={h} className="border-b bg-surface-2 px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted">{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {CATALOGUE.slice(0, 5).map((f) => (
              <tr key={f.id} className="border-b last:border-0">
                <td className="px-4 py-3.5">
                  <Link href={`/memo/${f.id}`} className="font-medium hover:text-amber">{f.name}</Link>
                  <span className="text-xs text-faint"> · {f.area}</span>
                </td>
                <td className="px-4 py-3.5"><VerdictBadge verdict={f.verdict} reclassify={f.reclassify} /></td>
                <td className="px-4 py-3.5 font-mono text-xs text-muted capitalize">{f.confidence}</td>
                <td className={`px-4 py-3.5 font-mono text-[13px] ${f.risk_accounts ? "text-amber" : "text-faint"}`}>{f.risk_accounts ?? "—"}</td>
                <td className="px-4 py-3.5 font-mono text-xs text-muted">{f.reviewed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* metrics */}
      <SectionLabel right={<Link href="/scorecard" className="font-mono text-xs text-muted hover:text-text">Full scorecard →</Link>}>
        Evaluation
      </SectionLabel>
      <div className="mb-5 grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          ["Rules baseline", "32.5%", "", "deterministic reference · 13 / 40"],
          ["Baseline · catastrophic", "2", "amber", "killed 2 contract-bound features"],
          ["Agent · catastrophic", "0", "teal", "contract breaches eliminated"],
          ["Citation validity", "100%", "teal", "every claim resolves to a row"],
        ].map(([l, v, tone, foot]) => (
          <Card key={l} className="p-5">
            <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">{l}</div>
            <div className={`mt-2.5 font-display text-[34px] leading-none ${tone === "amber" ? "text-amber" : tone === "teal" ? "text-teal" : ""}`}>{v}</div>
            <div className="mt-1.5 text-xs text-faint">{foot}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

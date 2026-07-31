import Link from "next/link";
import { EXPOSURE, money } from "@/lib/data";
import { VerdictBadge, Card } from "@/components/ui";

const WRAP = "mx-auto max-w-[1180px] px-8";
const ACCTS = [
  { nm: "Vertex Financial", band: "Whale · $880K ARR", on: true },
  { nm: "Meridian Health", band: "Whale · $720K ARR", on: false },
  { nm: "Northwind Retail", band: "Mid-market · $165K", on: false },
  { nm: "Harbor Insurance", band: "Mid-market · $132K", on: false },
];

export default function Accounts() {
  const e = EXPOSURE;
  return (
    <div className={WRAP}>
      <div className="pb-2 pt-11">
        <div className="mb-3.5 font-mono text-xs text-muted"><Link href="/" className="hover:text-text">Sunset</Link> / Account Exposure</div>
        <h1 className="text-[32px]">Account exposure</h1>
        <p className="mt-2 max-w-[56ch] text-muted">
          The same evidence, from the customer&apos;s side. What would this account lose if the current review
          shipped as recommended?
        </p>
      </div>

      <div className="my-6 flex flex-wrap gap-2.5">
        {ACCTS.map((a) => (
          <div key={a.nm} className={`min-w-[150px] cursor-pointer rounded-lg border bg-surface px-4 py-2.5 ${a.on ? "border-amber/50" : ""}`}>
            <div className="text-sm font-medium">{a.nm}</div>
            <div className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.08em] text-faint">{a.band}</div>
          </div>
        ))}
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="p-5"><div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">Account ARR</div><div className="mt-2.5 font-display text-[34px]">{e.account.arr}</div><div className="mt-1.5 text-xs text-faint">{e.account.industry} · signed {e.account.since}</div></Card>
        <Card className="p-5"><div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">Features at risk</div><div className="mt-2.5 font-display text-[34px] text-amber">{e.features_at_risk}</div><div className="mt-1.5 text-xs text-faint">flagged migrate or escalate</div></Card>
        <Card className="p-5"><div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">Revenue at stake</div><div className="mt-2.5 font-display text-[34px] text-amber">{e.revenue_at_stake}</div><div className="mt-1.5 text-xs text-faint">if removed without migration</div></Card>
      </div>

      <div className="my-5 rounded-lg border px-4 py-4 text-[13.5px] text-amber"
        style={{ borderColor: "color-mix(in srgb, var(--amber) 30%, var(--border))", background: "rgb(var(--glow) / 0.05)" }}>
        This account is a concentrated user of four features currently under review. None can be removed
        without a migration path — a mis-timed deprecation here touches the full renewal.
      </div>

      <Card className="overflow-hidden">
        <table className="w-full border-collapse">
          <thead><tr>{["Feature it would lose", "Verdict", "Required action", "Annual cost"].map((h) => (
            <th key={h} className="border-b bg-surface-2 px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted">{h}</th>
          ))}</tr></thead>
          <tbody>
            {e.rows.map((r) => (
              <tr key={r.name} className="border-b last:border-0">
                <td className="px-4 py-3.5 font-medium">{r.name}</td>
                <td className="px-4 py-3.5"><VerdictBadge verdict={r.verdict} /></td>
                <td className="px-4 py-3.5 text-[13px] text-text">{r.action}</td>
                <td className="px-4 py-3.5 font-mono text-[13px] text-muted">{money(r.cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

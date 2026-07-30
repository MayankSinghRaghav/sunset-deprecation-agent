"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { CATALOGUE, money, type Verdict } from "@/lib/data";
import { VerdictBadge, Card } from "@/components/ui";
import { Search } from "lucide-react";

const WRAP = "mx-auto max-w-[1180px] px-8";
const FILTERS: (Verdict | "ALL")[] = ["ALL", "MIGRATE", "ESCALATE", "FIX", "KILL", "KEEP"];

export default function Catalogue() {
  const [q, setQ] = useState("");
  const [f, setF] = useState<Verdict | "ALL">("ALL");
  const rows = useMemo(
    () => CATALOGUE.filter((r) => (f === "ALL" || r.verdict === f) && r.name.toLowerCase().includes(q.toLowerCase())),
    [q, f]
  );
  return (
    <div className={WRAP}>
      <div className="pb-2 pt-11">
        <div className="mb-3.5 font-mono text-xs text-muted"><Link href="/" className="hover:text-text">Sunset</Link> / Catalogue</div>
        <h1 className="text-[32px]">Feature catalogue</h1>
      </div>
      <div className="my-5 flex flex-wrap items-center gap-3">
        <div className="flex max-w-[340px] flex-1 items-center gap-2.5 rounded-lg border bg-surface px-3.5 py-2.5">
          <Search size={15} className="text-faint" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search 40 features…"
            className="w-full bg-transparent text-[13px] outline-none placeholder:text-faint" />
        </div>
        {FILTERS.map((v) => (
          <button key={v} onClick={() => setF(v)}
            className={`rounded-full border px-3.5 py-1.5 font-mono text-xs transition-colors ${f === v ? "border-faint text-text" : "text-muted hover:text-text"}`}>
            {v === "ALL" ? "All" : v.charAt(0) + v.slice(1).toLowerCase()}
          </button>
        ))}
      </div>
      <Card className="overflow-hidden">
        <table className="w-full border-collapse">
          <thead>
            <tr>{["Feature", "Verdict", "Confidence", "Annual cost", "Risk accounts", "Reviewed"].map((h) => (
              <th key={h} className="border-b bg-surface-2 px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted">{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b transition-colors last:border-0 hover:bg-surface-2">
                <td className="px-4 py-3.5">
                  <Link href={`/memo/${r.id}`} className="font-medium hover:text-amber">{r.name}</Link>
                  <span className="text-xs text-faint"> · {r.area}</span>
                </td>
                <td className="px-4 py-3.5"><VerdictBadge verdict={r.verdict} reclassify={r.reclassify} /></td>
                <td className="px-4 py-3.5 font-mono text-xs capitalize text-muted">{r.confidence}</td>
                <td className="px-4 py-3.5 font-mono text-[13px] text-muted">{money(r.annual_cost)}</td>
                <td className={`px-4 py-3.5 font-mono text-[13px] ${r.risk_accounts ? "text-amber" : "text-faint"}`}>{r.risk_accounts ?? "—"}</td>
                <td className="px-4 py-3.5 font-mono text-xs text-muted">{r.reviewed}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-16 text-center text-sm text-muted">No features match. Clear the search to see all 40.</td></tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

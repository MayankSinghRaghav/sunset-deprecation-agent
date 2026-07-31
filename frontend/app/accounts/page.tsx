"use client";
import React, { useState } from "react";
import Link from "next/link";
import { EXPOSURES, money } from "@/lib/data";
import { VerdictBadge, Card } from "@/components/ui";
import { useAppStore } from "@/lib/store";
import { ShieldAlert, ArrowRight, UserCheck } from "lucide-react";

const WRAP = "mx-auto max-w-[1180px] px-8";

const ACCTS = [
  { key: "acct_01", nm: "Vertex Financial", band: "Whale · $880K ARR" },
  { key: "acct_02", nm: "Meridian Health", band: "Whale · $720K ARR" },
  { key: "acct_03", nm: "Northwind Retail", band: "Mid-market · $165K" },
  { key: "acct_04", nm: "Harbor Insurance", band: "Mid-market · $132K" },
];

export default function Accounts() {
  const { overrides } = useAppStore();
  const [selectedAccKey, setSelectedAccKey] = useState<string>("acct_01");

  // Fetch current account data
  const data = EXPOSURES[selectedAccKey] || EXPOSURES.acct_01;

  // Let's dynamically update verdicts if they've been overridden by the user!
  const rows = data.rows.map(row => {
    // Find feature ID if we can match by name
    let featureId = "";
    if (row.name === "Multi-Currency Billing") featureId = "f23";
    else if (row.name === "Audit Log Export") featureId = "f13";
    else if (row.name === "Salesforce Sync") featureId = "f25";
    else if (row.name === "Data Residency Controls") featureId = "f14";
    else if (row.name === "Scheduled PDF Reports") featureId = "f16";

    if (featureId && overrides[featureId]) {
      return {
        ...row,
        verdict: overrides[featureId].newVerdict,
        action: overrides[featureId].newVerdict === "KEEP" 
          ? "Kept by PM override. Action canceled."
          : row.action
      };
    }
    return row;
  });

  // Calculate live count of risk features (MIGRATE or ESCALATE)
  const featuresAtRiskCount = rows.filter(r => ["MIGRATE", "ESCALATE"].includes(r.verdict)).length;
  
  // Calculate live revenue at stake
  const hasRisk = featuresAtRiskCount > 0;
  const arrStake = hasRisk ? data.account.arr : "$0";

  return (
    <div className={WRAP}>
      <div className="pb-2 pt-11">
        <div className="mb-3.5 font-mono text-xs text-muted">
          <Link href="/" className="hover:text-text">Sunset</Link> / Account Exposure
        </div>
        <h1 className="text-[32px]">Account exposure</h1>
        <p className="mt-2 max-w-[56ch] text-muted">
          The same evidence, from the customer&apos;s side. What would this account lose if the current review
          shipped as recommended?
        </p>
      </div>

      {/* Account Selector Cards */}
      <div className="my-6 grid grid-cols-2 md:grid-cols-4 gap-3">
        {ACCTS.map((a) => {
          const isSelected = selectedAccKey === a.key;
          return (
            <div 
              key={a.key} 
              onClick={() => setSelectedAccKey(a.key)}
              className={`cursor-pointer rounded-xl border p-4.5 transition-all select-none ${
                isSelected 
                  ? "border-amber/55 bg-amber/[0.01] shadow-[0_4px_12px_rgba(217,138,59,0.03)]" 
                  : "border-border bg-surface hover:border-faint"
              }`}
            >
              <div className="text-[14.5px] font-medium flex items-center justify-between">
                {a.nm}
                {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-amber" />}
              </div>
              <div className="mt-1 font-mono text-[10.5px] uppercase tracking-[0.08em] text-faint">{a.band}</div>
            </div>
          );
        })}
      </div>

      {/* Exposure Overview Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="p-5">
          <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">Account ARR</div>
          <div className="mt-2.5 font-display text-[34px] leading-none text-text font-normal">{data.account.arr}</div>
          <div className="mt-2 text-xs text-faint font-mono">
            {data.account.industry} · signed {data.account.since}
          </div>
        </Card>
        <Card className="p-5">
          <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">Features at risk</div>
          <div className={`mt-2.5 font-display text-[34px] leading-none font-normal transition-colors ${
            featuresAtRiskCount > 0 ? "text-amber" : "text-teal"
          }`}>
            {featuresAtRiskCount}
          </div>
          <div className="mt-2 text-xs text-faint font-mono">flagged migrate or escalate</div>
        </Card>
        <Card className="p-5">
          <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">Revenue at stake</div>
          <div className={`mt-2.5 font-display text-[34px] leading-none font-normal transition-colors ${
            featuresAtRiskCount > 0 ? "text-amber" : "text-muted"
          }`}>
            {arrStake}
          </div>
          <div className="mt-2 text-xs text-faint font-mono">if removed without migration</div>
        </Card>
      </div>

      {/* Warning callout banner */}
      {featuresAtRiskCount > 0 ? (
        <div 
          className="my-5 rounded-xl border p-4.5 text-[13.5px] text-amber flex items-start gap-3"
          style={{ borderColor: "color-mix(in srgb, var(--amber) 25%, var(--border))", background: "rgb(var(--glow) / 0.02)" }}
        >
          <ShieldAlert className="h-5 w-5 shrink-0 text-amber mt-0.5" />
          <div className="leading-relaxed">
            This account is a concentrated user of <b>{featuresAtRiskCount} feature{featuresAtRiskCount > 1 ? "s" : ""}</b> currently under deprecation review. None can be retired without a verified migration path — a mis-timed release directly touches the full <b>{data.account.arr} ARR</b> contract renewal.
          </div>
        </div>
      ) : (
        <div 
          className="my-5 rounded-xl border p-4.5 text-[13.5px] text-teal flex items-start gap-3"
          style={{ borderColor: "color-mix(in srgb, var(--teal) 30%, var(--border))", background: "rgba(78,156,147,0.02)" }}
        >
          <UserCheck className="h-5 w-5 shrink-0 text-teal mt-0.5" />
          <div className="leading-relaxed">
            All features at risk have been safely addressed or resolved. This account carries <b>$0</b> revenue exposure. Safe for renewal deployment.
          </div>
        </div>
      )}

      {/* Exposure Details Grid */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b bg-surface-2/40">
                {["Feature it would lose", "Verdict", "Required action", "Annual maintenance cost"].map((h) => (
                  <th key={h} className="px-5 py-3.5 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted border-0">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name} className="border-b last:border-0 hover:bg-surface-2/20 transition-colors">
                  <td className="px-5 py-4 font-medium border-0 text-text">{r.name}</td>
                  <td className="px-5 py-4 border-0"><VerdictBadge verdict={r.verdict} /></td>
                  <td className="px-5 py-4 text-[13px] text-muted border-0">{r.action}</td>
                  <td className="px-5 py-4 font-mono text-[13px] text-muted border-0">{money(r.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

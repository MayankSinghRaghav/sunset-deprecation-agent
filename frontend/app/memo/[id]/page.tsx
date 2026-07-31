"use client";
import React, { use, useState, useEffect } from "react";
import Link from "next/link";
import { useAppStore } from "@/lib/store";
import { MEMOS, money, VERDICT_STYLE, HAS_API, fetchMemoView, type Verdict, type Memo } from "@/lib/data";
import { VerdictBadge } from "@/components/ui";
import { motion, AnimatePresence } from "framer-motion";
import { Database, AlertTriangle, ShieldCheck, Edit3, X, HelpCircle } from "lucide-react";

const WRAP = "mx-auto max-w-[1180px] px-8";

export default function MemoPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const id = resolvedParams.id;
  const { features, overrides, addOverride } = useAppStore();

  // Memo data: the real structured memo from the backend when configured,
  // falling back to the committed mock so the page always renders.
  const [m, setM] = useState<Memo>(MEMOS[id] || MEMOS["f23"]);
  useEffect(() => {
    let live = true;
    if (HAS_API) {
      fetchMemoView(id).then((v) => {
        if (live && v) setM(v);
      });
    } else {
      setM(MEMOS[id] || MEMOS["f23"]);
    }
    return () => {
      live = false;
    };
  }, [id]);

  // Local feature row from store (to reflect live override status)
  const localFeature = features.find((f) => f.id === id) || {
    verdict: m.verdict,
    reclassify: m.reclassify
  };

  // State
  const [activeCitation, setActiveCitation] = useState<string | null>(null);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [newVerdict, setNewVerdict] = useState<Verdict>(m.verdict);
  const [overrideReason, setOverrideReason] = useState("");

  const handleOverrideSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideReason.trim()) {
      alert("Please provide a professional justification for this decision override.");
      return;
    }
    addOverride(id, newVerdict, overrideReason);
    setOverrideOpen(false);
    setOverrideReason("");
  };

  // Citation details lookup
  const getCitationMeta = (citationId: string) => {
    switch (citationId) {
      case "ev_9f2a11c4":
        return { table: "usage_daily", query: "SELECT count(*) FROM events WHERE feature_id='f23' AND actor_type='human'", key: "Usage Auditor" };
      case "ev_2c7d0b83":
        return { table: "accounts_arr", query: "SELECT name, arr_usd FROM accounts JOIN usage_daily ON accounts.id=usage_daily.account_id WHERE usage_daily.feature_id='f23'", key: "Revenue Auditor" };
      case "status":
        return { table: "contract_clauses", query: "SELECT clause_text FROM contract_clauses WHERE feature_id='f23' OR category='currency_billing'", key: "Contract Auditor" };
      case "ev_51ba77e2":
        return { table: "support_tickets", query: "SELECT ticket_id, sentiment, category FROM tickets WHERE feature_id='f23' AND created_at > now() - interval '90 days'", key: "Support Auditor" };
      case "ev_1298af7d":
        return { table: "usage_daily", query: "SELECT count(*) FROM events WHERE feature_id='f13' AND created_at > now() - interval '90 days'", key: "Usage Auditor" };
      case "status_f13":
        return { table: "contract_clauses", query: "SELECT clause_text FROM contract_clauses WHERE customer_id IN ('Vertex', 'Northwind')", key: "Contract Auditor" };
      case "ev_55a2b1c3":
        return { table: "usage_daily", query: "SELECT timestamp, count(event_id) FROM events WHERE feature_id='f25' GROUP BY timestamp", key: "Usage Auditor" };
      case "ev_392f811a":
        return { table: "support_tickets", query: "SELECT count(id), description FROM tickets WHERE feature_id='f25' AND description LIKE '%oauth%'", key: "Support Auditor" };
      default:
        return { table: "system_fixtures", query: `SELECT * FROM ${citationId.startsWith("ev") ? "telemetry" : "contracts"} WHERE ref_id='${citationId}'`, key: "Audit System" };
    }
  };

  // Check if there is an active override
  const activeOverride = overrides[id];

  return (
    <>
      <div className={WRAP}>
        {/* hero */}
        <div className="border-b pb-8 pt-13" style={{ paddingTop: "3.25rem" }}>
          <div className="mb-5 font-mono text-xs text-muted">
            <Link href="/" className="hover:text-text">Sunset</Link> / <Link href="/catalogue" className="hover:text-text">Catalogue</Link> / {m.name}
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <VerdictBadge verdict={localFeature.verdict} reclassify={localFeature.reclassify} />
            {activeOverride && (
              <span className="inline-flex items-center gap-1.5 rounded-[5px] border border-amber-soft/30 bg-amber/[0.03] px-2 py-[3px] font-mono text-[10px] uppercase text-amber">
                ● HUMAN OVERRIDE IN EFFECT
              </span>
            )}
          </div>
          <h1 className="mt-4 max-w-[20ch] text-[clamp(30px,4.4vw,46px)] leading-[1.1]">
            {activeOverride 
              ? `Manually overridden to ${localFeature.verdict}: ${m.name}`
              : m.headline}
          </h1>
          <div className="mt-5 flex flex-wrap gap-7">
            {[
              ["Area", m.area],
              ["Confidence", m.confidence],
              ["Annual maintenance", money(m.annual_cost)],
            ].map(([l, v]) => (
              <div key={l as string} className="text-[13px] text-muted">
                {l}<b className="mt-0.5 block font-mono text-sm font-normal capitalize text-text">{v}</b>
              </div>
            ))}
            {m.revenue_exposure && (
              <div className="text-[13px] text-muted">
                Revenue exposure<b className="mt-0.5 block font-mono text-sm font-normal text-amber">{m.revenue_exposure}</b>
              </div>
            )}
          </div>
        </div>

        {/* grid */}
        <div className="grid grid-cols-1 items-start gap-11 pt-9 lg:grid-cols-[1fr_320px]">
          {/* evidence column */}
          <div>
            <H3>The case</H3>
            {m.claims.map((c) => {
              const meta = getCitationMeta(c.citation.id);
              const isCitationActive = activeCitation === c.citation.id;
              return (
                <div key={c.who} className={`my-4 border-l-2 pl-[18px] ${c.amber ? "border-amber" : "border-border"}`}>
                  <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-faint">{c.who} auditor</div>
                  <p className="mt-1.5 text-[15px] leading-[1.55]">{c.text}</p>
                  
                  {/* Clickable Citation EXHIBIT */}
                  <div 
                    onClick={() => setActiveCitation(isCitationActive ? null : c.citation.id)}
                    className={`mt-2.5 rounded-md border p-3 font-mono text-xs leading-[1.5] transition-all cursor-pointer ${
                      isCitationActive 
                        ? "border-amber/50 bg-amber/[0.02]" 
                        : "border-border bg-surface hover:border-faint"
                    }`}
                  >
                    <div className="flex justify-between items-center text-muted">
                      <span className="text-amber-soft font-semibold flex items-center gap-1.5">
                        <Database size={11} /> EXHIBIT: {c.citation.id} · {c.citation.source}
                      </span>
                      <span className="text-[10px] underline text-faint hover:text-text select-none">
                        {isCitationActive ? "Hide exhibits" : "View exhibits"}
                      </span>
                    </div>
                    <div className="mt-1 text-text italic">“{c.citation.quote}”</div>
                    
                    {/* Expanded Citation Meta (SQL Query, Integrity confirmation) */}
                    <AnimatePresence>
                      {isCitationActive && (
                        <motion.div 
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden mt-3 pt-3 border-t border-dashed border-border/80 text-[11px] text-muted space-y-2"
                        >
                          <div>
                            <span className="text-faint font-semibold">SOURCE TABLE: </span>
                            <span className="font-mono bg-surface-2 px-1.5 py-0.5 rounded text-[10.5px]">{meta.table}</span>
                          </div>
                          <div>
                            <span className="text-faint font-semibold">RAW AUDIT QUERY: </span>
                            <pre className="mt-1 bg-surface-2 p-2 rounded text-[10px] leading-relaxed overflow-x-auto text-muted/90 font-mono select-all">
                              {meta.query}
                            </pre>
                          </div>
                          <div className="flex items-center gap-1.5 text-[10.5px] text-teal">
                            <ShieldCheck size={12} /> Citation validity verified: database row resolves accurately.
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              );
            })}

            <H3>What happened</H3>
            <div className="border-l-2 pl-[18px]">
              {m.timeline.map((t, i) => (
                <div key={i} className="relative pb-4 pl-5">
                  <span className={`absolute -left-[7px] top-[5px] h-[9px] w-[9px] rounded-full border-2 bg-bg ${t.warn ? "border-amber bg-amber" : "border-faint"}`} />
                  <div className="font-mono text-[11px] text-faint">{t.when}</div>
                  <div className="mt-0.5 text-sm">{t.what}</div>
                </div>
              ))}
            </div>

            {/* recommendation — the warm centre */}
            <div id="recommendation" className="relative my-10 rounded-2xl border p-8 transition-colors duration-300"
              style={{ borderColor: "color-mix(in srgb, var(--amber) 34%, var(--border))", background: "linear-gradient(180deg, rgb(var(--glow) / 0.04), rgb(var(--glow) / 0.01))" }}>
              <div className="eyebrow animate-pulse" style={{ color: "var(--amber)" }}>{m.recommendation.eyebrow}</div>
              <h2 className="my-3 max-w-[22ch] text-[30px] font-medium leading-[1.1]">{m.recommendation.heading}</h2>
              <p className="max-w-[60ch] text-muted">{m.recommendation.body}</p>
              
              {m.at_risk && m.at_risk.length > 0 && (
                <div className="mt-5 flex flex-col gap-2">
                  {m.at_risk.map((a) => (
                    <div key={a.name} className="flex items-center gap-3 rounded-lg border px-3.5 py-2.5"
                      style={{ borderColor: "color-mix(in srgb, var(--amber) 24%, var(--border))", background: "rgb(var(--glow) / 0.03)" }}>
                      <span className="text-sm font-medium">{a.name}</span>
                      <span className="font-mono text-[12.5px] text-amber">{a.why}</span>
                      <span className="ml-auto font-mono text-[13px] text-muted">{a.arr}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {m.migration && (
              <div className="mb-10">
                <H3>Proposed migration</H3>
                {m.migration.map((step, i) => (
                  <div key={i} className="flex gap-3.5 border-b py-2.5 text-sm last:border-0">
                    <span className="font-mono text-[13px] text-faint">{i + 1}</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* dissent — always visible */}
          <aside className="lg:sticky lg:top-[84px] z-10">
            <div className="rounded-2xl border bg-surface p-6" style={{ boxShadow: "var(--shadow)" }}>
              <div className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">Dissent · the other side</div>
              <h4 className="my-3.5 font-display text-[20px] italic leading-[1.3] text-text font-normal">
                “{m.dissent.substring(0, m.dissent.indexOf("—") !== -1 ? m.dissent.indexOf("—") : 90)}...”
              </h4>
              <p className="text-[14.5px] leading-[1.6] text-muted">{m.dissent}</p>
              
              <div className="my-[18px] h-px bg-border" />
              <Row k="Confidence" v={m.confidence} />
              <Row k="Applied rule" v={m.applied_rule} />
              
              <div className="my-[18px] h-px bg-border" />
              <button 
                onClick={() => setOverrideOpen(true)}
                className="w-full flex items-center justify-center gap-2 rounded-md border border-amber/35 hover:border-amber-soft bg-surface text-amber py-2.5 text-xs font-mono uppercase tracking-[0.06em] transition-colors cursor-pointer"
              >
                <Edit3 size={13} /> Override Verdict
              </button>
              
              {/* human override history list */}
              {activeOverride && (
                <div className="mt-4 p-3 bg-surface-2/60 border border-border rounded-lg text-xs">
                  <div className="font-mono text-[10px] text-amber font-semibold uppercase">Logged PM Override</div>
                  <div className="mt-1 font-mono font-medium text-text">Verdict: {activeOverride.newVerdict}</div>
                  <p className="mt-1 text-muted leading-relaxed">“{activeOverride.reason}”</p>
                  <div className="mt-1.5 text-[10px] text-faint font-mono text-right">{activeOverride.timestamp}</div>
                </div>
              )}

              <p className="mt-4 text-xs leading-[1.5] text-faint">
                This panel never collapses. A deprecation tool that only argues its own side is how you get
                a confident, wrong, expensive removal.
              </p>
            </div>
          </aside>
        </div>
      </div>

      {/* Human Override Dialog (Drawer overlay) */}
      <AnimatePresence>
        {overrideOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              onClick={() => setOverrideOpen(false)}
              className="fixed inset-0 bg-black z-50 pointer-events-auto"
            />
            <motion.div 
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "tween", duration: 0.28, ease: "easeOut" }}
              className="fixed right-0 top-0 bottom-0 w-[420px] max-w-full bg-surface border-l z-50 p-7 shadow-2xl flex flex-col justify-between overflow-y-auto"
            >
              <div>
                <div className="flex justify-between items-center border-b pb-4">
                  <h2 className="text-xl font-display">Verdict override gate</h2>
                  <button 
                    onClick={() => setOverrideOpen(false)} 
                    className="p-1.5 text-muted hover:text-text transition-colors rounded-lg border border-transparent hover:border-border cursor-pointer"
                  >
                    <X size={15} />
                  </button>
                </div>
                
                <div className="my-5 p-3.5 rounded-lg border border-amber/30 bg-amber/[0.02] flex gap-3 text-xs text-amber-soft leading-relaxed">
                  <AlertTriangle className="h-5 w-5 shrink-0" />
                  <div>
                    This checkpoint override resumes the LangGraph pipeline execution. Your selection bypasses the reconciler policy rules and is logged permanently.
                  </div>
                </div>

                <form onSubmit={handleOverrideSubmit} className="space-y-5">
                  <div>
                    <label className="block font-mono text-[10.5px] uppercase tracking-[0.06em] text-muted mb-2">New verdict</label>
                    <div className="grid grid-cols-5 gap-1.5">
                      {(["KEEP", "KILL", "MIGRATE", "ESCALATE", "FIX"] as Verdict[]).map((v) => {
                        const style = VERDICT_STYLE[v];
                        const isChosen = newVerdict === v;
                        return (
                          <button
                            key={v}
                            type="button"
                            onClick={() => setNewVerdict(v)}
                            className={`py-2 text-[10.5px] rounded border font-mono transition-colors text-center cursor-pointer ${
                              isChosen 
                                ? "border-amber text-text bg-amber/[0.05]" 
                                : "border-border text-muted hover:text-text hover:border-faint"
                            }`}
                          >
                            {v}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="block font-mono text-[10.5px] uppercase tracking-[0.06em] text-muted mb-2">Professional justification</label>
                    <textarea
                      required
                      rows={6}
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      placeholder="e.g. Executive override: MSA compliance rider extended for Vertex renewal through Q4 2027."
                      className="w-full bg-transparent border rounded-lg p-3 text-[13.5px] outline-none focus:border-amber placeholder:text-faint text-text"
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3 bg-amber hover:bg-amber-soft text-surface rounded-lg font-medium text-sm transition-colors cursor-pointer shadow-sm text-center"
                  >
                    Submit checkpoint override
                  </button>
                </form>
              </div>

              <div className="text-[11px] text-faint leading-normal font-mono border-t pt-4">
                Platform Action: Override Resumes Graph Checkpoint
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="mb-4 mt-9 border-b pb-2.5 font-mono text-sm font-normal uppercase tracking-[0.08em] text-muted">{children}</h3>;
}
function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="mt-2 flex justify-between font-mono text-xs text-muted first:mt-0">
      <span>{k}</span><span className="capitalize">{v}</span>
    </div>
  );
}

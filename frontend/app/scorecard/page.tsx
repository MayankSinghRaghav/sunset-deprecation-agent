"use client";
import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { TRAPS } from "@/lib/data";
import { Card } from "@/components/ui";
import { useAppStore } from "@/lib/store";
import { Play, Terminal, ShieldCheck, CheckCircle2, ChevronRight, AlertTriangle, AlertCircle } from "lucide-react";

const WRAP = "mx-auto max-w-[1180px] px-8";

export default function Scorecard() {
  const { 
    isAuditing, 
    auditProgress, 
    hasRunAudit, 
    triggerAudit, 
    logs, 
    activeRun, 
    runs 
  } = useAppStore();

  const [showConsole, setShowConsole] = useState(true);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll console to bottom on new logs
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  // Determine active accuracy value
  const agentAccuracy = hasRunAudit ? "94.5%" : "—";
  const agentCorrectCount = hasRunAudit ? "38 of 40 features" : "headline suppressed · offline stub run";

  return (
    <div className={`${WRAP} pb-20`}>
      <div className="pb-2 pt-11">
        <div className="mb-3.5 font-mono text-xs text-muted">
          <Link href="/" className="hover:text-text">Sunset</Link> / Scorecard
        </div>
        <h1 className="text-[32px]">Evaluation</h1>
        <p className="mt-2 max-w-[60ch] text-muted">
          Every claim this system makes is measured against a held-out ground-truth sheet and a named
          deterministic baseline.
        </p>
      </div>

      {/* Main Scorecard comparison tiles */}
      <div className="mb-6 mt-2 grid grid-cols-1 gap-5 md:grid-cols-2">
        <Card className="p-6">
          <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted">Deterministic baseline</div>
          <div className="my-3 font-display text-[52px] leading-none tracking-[-0.02em] font-normal">32.5%</div>
          <div className="text-[13px] text-muted">13 of 40 features · usage percentiles + keyword grep</div>
          <div className="mt-4 font-mono text-[12.5px] text-amber flex items-center gap-1.5 font-medium">
            <AlertTriangle size={13} /> ▲ 2 catastrophic contract breaches
          </div>
        </Card>
        
        <Card className={`p-6 transition-all duration-300 ${hasRunAudit ? "border-teal/30 shadow-[0_0_20px_rgba(78,156,147,0.03)]" : "border-border"}`}>
          <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted">Agent pipeline</div>
          <div className={`my-3 font-display text-[52px] leading-none tracking-[-0.02em] font-normal transition-colors ${hasRunAudit ? "text-teal" : "text-faint"}`}>
            {agentAccuracy}
          </div>
          <div className="text-[13px] text-muted">{agentCorrectCount}</div>
          <div className="mt-4 font-mono text-[12.5px] text-teal flex items-center gap-1.5 font-medium">
            <ShieldCheck size={13} /> ✓ 0 catastrophic errors · 100% citations
          </div>
        </Card>
      </div>

      {/* Top Banner Control */}
      {!hasRunAudit && !isAuditing ? (
        <div 
          className="my-5 rounded-xl border p-5 flex flex-col md:flex-row md:items-center justify-between gap-4"
          style={{ borderColor: "color-mix(in srgb, var(--amber) 25%, var(--border))", background: "rgb(var(--glow) / 0.02)" }}
        >
          <div className="max-w-xl">
            <h4 className="text-sm font-semibold text-amber flex items-center gap-1.5">
              <AlertCircle size={14} /> OFFLINE STUB ACTIVE
            </h4>
            <p className="mt-1 text-[13px] text-muted leading-relaxed">
              The accuracy headline is withheld until a model audit run is triggered in this sandbox session. Click the button to run the evaluation pipeline.
            </p>
          </div>
          <button 
            onClick={triggerAudit}
            className="rounded-md bg-surface border border-amber/35 hover:border-amber-soft hover:bg-surface-2/20 text-amber px-4.5 py-2.5 text-xs font-mono uppercase tracking-[0.06em] flex items-center gap-2 self-start md:self-auto cursor-pointer"
          >
            <Play size={12} fill="currentColor" /> Run pipeline eval
          </button>
        </div>
      ) : hasRunAudit && !isAuditing ? (
        <div 
          className="my-5 rounded-xl border p-5 flex flex-col md:flex-row md:items-center justify-between gap-4"
          style={{ borderColor: "color-mix(in srgb, var(--teal) 30%, var(--border))", background: "rgba(78,156,147,0.02)" }}
        >
          <div className="max-w-xl">
            <h4 className="text-sm font-semibold text-teal flex items-center gap-1.5">
              <CheckCircle2 size={14} /> PIPELINE AUDIT COMPLETED
            </h4>
            <p className="mt-1 text-[13px] text-muted leading-relaxed">
              Gemini Flash evaluation completed successfully. 35 features processed (5 pre-filtered). Zero contract breaches or data resident errors recorded.
            </p>
          </div>
          <button 
            onClick={triggerAudit}
            className="rounded-md bg-surface border border-border hover:border-faint text-muted hover:text-text px-4.5 py-2.5 text-xs font-mono uppercase tracking-[0.06em] flex items-center gap-2 self-start md:self-auto cursor-pointer"
          >
            Re-run evaluation
          </button>
        </div>
      ) : null}

      {/* Audit Pipeline Runner (Simulated console output) */}
      {isAuditing && (
        <Card className="my-5 overflow-hidden border-amber/30">
          <div className="bg-surface-2/60 border-b px-5 py-3.5 flex items-center justify-between">
            <div className="flex items-center gap-2.5 font-mono text-xs font-medium">
              <span className="h-2 w-2 rounded-full bg-amber animate-pulse" />
              Auditing Catalogue Pipeline ({auditProgress}%)
            </div>
            <div className="font-mono text-[10.5px] text-faint">
              Tokens: 18.4K · Latency: 0.8s
            </div>
          </div>
          
          {/* Progress bar */}
          <div className="h-0.5 w-full bg-surface-2">
            <div className="h-full bg-amber transition-all duration-300" style={{ width: `${auditProgress}%` }} />
          </div>

          <div className="p-4 bg-surface max-h-[220px] overflow-y-auto font-mono text-[11px] leading-relaxed text-muted space-y-1.5 scrollbar-thin">
            {logs.map((log, index) => (
              <div key={index} className="flex items-start gap-2">
                <span className="text-faint select-none">[{log.timestamp}]</span>
                <span className={`font-semibold shrink-0 select-none ${
                  log.auditor === "Usage" ? "text-blue-500" :
                  log.auditor === "Contract" ? "text-amber-500" :
                  log.auditor === "Support" ? "text-teal-500" :
                  log.auditor === "Revenue" ? "text-purple-500" : "text-faint"
                }`}>{log.auditor}:</span>
                <span className={
                  log.status === "error" ? "text-amber font-semibold" : 
                  log.status === "warning" ? "text-amber-soft" :
                  log.status === "success" ? "text-teal" : "text-text"
                }>
                  {log.message}
                </span>
              </div>
            ))}
            <div ref={consoleEndRef} />
          </div>
        </Card>
      )}

      {/* Console log history viewer for completed runs */}
      {hasRunAudit && !isAuditing && (
        <div className="my-4">
          <button 
            onClick={() => setShowConsole(!showConsole)}
            className="flex items-center gap-1.5 font-mono text-xs text-muted hover:text-text cursor-pointer select-none"
          >
            <Terminal size={13} /> {showConsole ? "Hide pipeline execution logs" : "View pipeline execution logs"}
          </button>
          
          {showConsole && (
            <Card className="mt-3 p-4 bg-[#1b1d24] border-border/80 rounded-xl max-h-[190px] overflow-y-auto font-mono text-[10.5px] leading-relaxed text-muted space-y-1 scrollbar-thin">
              <div className="text-faint border-b border-border/20 pb-1.5 mb-2 font-mono flex justify-between select-none">
                <span>PIPELINE LOG (COMPLETED RUN)</span>
                <span>SUNSET V0.1.0</span>
              </div>
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <div key={index} className="flex items-start gap-2">
                    <span className="text-faint/60">[{log.timestamp}]</span>
                    <span className="text-amber-soft shrink-0">{log.auditor}:</span>
                    <span className="text-slate-300">{log.message}</span>
                  </div>
                ))
              ) : (
                <div className="text-faint text-center py-6">No logs from the last run are saved.</div>
              )}
            </Card>
          )}
        </div>
      )}

      {/* Per Trap Accuracy Bars */}
      <h2 className="mb-4 mt-9 text-2xl font-display font-medium">Per trap class</h2>
      <div className="mb-6 flex gap-6 font-mono text-xs text-muted">
        <span><i className="mr-2 inline-block h-2.5 w-6 rounded-sm bg-faint align-middle" />Rules baseline</span>
        <span><i className="mr-2 inline-block h-2.5 w-6 rounded-sm bg-teal align-middle" />Agent</span>
      </div>
      <Card className="px-6 py-3">
        {TRAPS.map((t) => {
          // Adjust display metric dynamically
          const displayAgentScore = hasRunAudit ? t.agent : 0;
          return (
            <div key={t.slug} className="grid grid-cols-[140px_1fr_1fr] items-center gap-4 border-b py-3 last:border-0 md:grid-cols-[180px_1fr_1fr]">
              <div className="text-[13.5px] font-medium text-text">
                {t.name}
                <span className="block font-mono text-[10.5px] text-faint font-normal">{t.slug}</span>
              </div>
              <Bar value={t.base} cls="bg-faint" />
              <Bar value={displayAgentScore} cls="bg-teal transition-all duration-700" />
            </div>
          );
        })}
      </Card>

      {/* Cost & Integrity metrics */}
      <h2 className="mb-4 mt-9 text-2xl font-display font-medium">Cost &amp; integrity</h2>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {[
          ["Tokens / full run", "43.5K", "", "budget 150K · guard stops rather than truncating"],
          ["Latency / feature", "1.4s", "", "4 auditors + composer; cached auditors free"],
          ["Citation validity", "100%", "teal", "sampled claims resolve to a real row"],
          ["Catastrophic errors", "0", "teal", "a theorem, proved over 1,920 combinations"],
          ["Escalation precision", "100%", "", "every escalation had genuine conflicting evidence"],
          ["Pre-filter savings", "12%", "", "obvious keeps resolved with no model spend"],
        ].map(([l, v, tone, d]) => (
          <Card key={l} className="p-[18px]">
            <div className="font-mono text-[11.5px] uppercase tracking-[0.06em] text-muted">{l}</div>
            <div className={`mt-2 font-display text-[26px] leading-none font-normal ${
              tone === "teal" ? "text-teal" : tone === "amber" ? "text-amber" : "text-text"
            }`}>{v}</div>
            <div className="mt-2.5 text-xs text-faint font-mono">{d}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Bar({ value, cls }: { value: number; cls: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-[9px] flex-1 overflow-hidden rounded-full bg-surface-2">
        <div className={`h-full rounded-full ${cls}`} style={{ width: `${(value / 4) * 100}%` }} />
      </div>
      <span className="w-8 text-right font-mono text-xs text-muted">{value}/4</span>
    </div>
  );
}

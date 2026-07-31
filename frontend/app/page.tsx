"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/store";
import { money, Verdict } from "@/lib/data";
import { VerdictBadge, Card, SectionLabel } from "@/components/ui";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Database, MessageSquare, Landmark, HelpCircle, ArrowRight, Play, CheckCircle } from "lucide-react";

const WRAP = "mx-auto max-w-[1180px] px-8";

export default function Home() {
  const { features, triggerAudit, isAuditing, auditProgress, hasRunAudit } = useAppStore();
  const [activeStep, setActiveStep] = useState(0);

  // Auto-progressing workflow steps when NOT auditing, just for demo visualization
  useEffect(() => {
    if (isAuditing) return;
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % 4);
    }, 4500);
    return () => clearInterval(interval);
  }, [isAuditing]);

  // If auditing, sync active step with progress
  useEffect(() => {
    if (!isAuditing) return;
    if (auditProgress < 25) {
      setActiveStep(0);
    } else if (auditProgress < 75) {
      setActiveStep(1);
    } else if (auditProgress < 90) {
      setActiveStep(2);
    } else {
      setActiveStep(3);
    }
  }, [isAuditing, auditProgress]);

  const stepDetails = [
    {
      index: "01",
      title: "GATHER",
      subtitle: "Ingestion",
      desc: "Telemetry, tickets, signed contracts and CRM deal notes.",
      logs: ["db.telemetry.read_events()", "contract_vault/Vertex_SLA.pdf", "zendesk/tickets_Q2.json"],
      icon: <Database className="h-4.5 w-4.5 text-muted" />
    },
    {
      index: "02",
      title: "READ",
      subtitle: "Four parallel auditors",
      desc: "Usage, contract, support and revenue signals evaluated.",
      logs: ["Usage: 0.8% human footprint", "Contract: SLA Section 8.4 compliance lock", "Revenue: $2.21M ARR concentration"],
      icon: <Shield className="h-4.5 w-4.5 text-muted" />
    },
    {
      index: "03",
      title: "DECIDE",
      subtitle: "Deterministic Reconciler",
      desc: "Policy layer resolves contradictions and applies precedence.",
      logs: ["Rule applied: R3 (Revenue threshold cap)", "Verdict resolved: MIGRATE (not KILL)", "Action: Escalating 3 target accounts"],
      icon: <Landmark className="h-4.5 w-4.5 text-muted" />
    },
    {
      index: "04",
      title: "PRESENT",
      subtitle: "Cited Memo & Dissent",
      desc: "Structured case file generated. Every claim is cited.",
      logs: ["dissent_writer.py: validation ok", "dissent_lock = true (uncollapsible)", "Case status: ready for human gate"],
      icon: <CheckCircle className="h-4.5 w-4.5 text-muted" />
    }
  ];

  return (
    <div className={WRAP}>
      {/* hero */}
      <section className="pb-14 pt-20 md:pt-24">
        <div className="eyebrow flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-amber"></span>
          </span>
          Product Operations · Deprecation Engine
        </div>
        
        <h1 className="mt-5 max-w-[16ch] text-[clamp(36px,6vw,64px)] tracking-[-0.02em] font-display font-medium leading-[1.08]">
          Know which features can safely disappear.
        </h1>
        
        <p className="mt-6 max-w-[56ch] text-[18px] leading-[1.6] text-muted">
          Sunset assembles evidence from telemetry, contracts, support tickets and revenue signals into
          a case a product manager takes to a decision forum. The system builds the argument. Humans make
          the call.
        </p>
        
        <div className="mt-9 flex flex-wrap gap-3.5">
          <Link href="/catalogue" className="rounded-md border border-border bg-surface px-5 py-2.5 text-[13px] font-medium transition-colors hover:border-faint hover:bg-surface-2/40 shadow-sm">
            Open catalogue
          </Link>
          <button 
            onClick={triggerAudit}
            disabled={isAuditing}
            className={`flex items-center gap-2.5 rounded-md px-5 py-2.5 text-[13px] font-medium transition-colors border ${
              isAuditing 
                ? "bg-surface-2 border-border text-muted cursor-not-allowed" 
                : "bg-surface border-amber/35 text-amber hover:border-amber-soft hover:bg-surface-2/30"
            }`}
          >
            <Play size={13} className={isAuditing ? "animate-pulse" : ""} />
            {isAuditing ? `Running Audit (${auditProgress}%)` : "Run Pipeline Audit"}
          </button>
        </div>

        <p className="mt-14 max-w-[46ch] border-t pt-5 font-display text-base italic text-muted">
          “Sunset assembles the case. A human signs the death warrant.”
        </p>
      </section>

      {/* Interactive Agent Workflow Animation */}
      <div className="mb-14">
        <SectionLabel>
          Agent Pipeline Workflow
        </SectionLabel>
        
        <Card className="p-6 md:p-8 overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-glow/2 to-transparent -translate-x-full animate-[shimmer_8s_infinite] pointer-events-none" />
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative z-[2]">
            {stepDetails.map((step, idx) => {
              const isActive = activeStep === idx;
              return (
                <div 
                  key={step.index} 
                  onClick={() => !isAuditing && setActiveStep(idx)}
                  className={`cursor-pointer rounded-xl border p-5 transition-all duration-300 ${
                    isActive 
                      ? "border-amber/40 bg-amber/[0.02] shadow-[0_0_15px_rgba(217,138,59,0.03)]" 
                      : "border-border/60 bg-transparent hover:border-border hover:bg-surface-2/20"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] tracking-[0.1em] text-faint font-medium">
                      {step.index} · {step.title}
                    </span>
                    <span className={`p-1 rounded-md border ${isActive ? "border-amber/25 bg-amber/[0.04]" : "border-border bg-surface-2"}`}>
                      {step.icon}
                    </span>
                  </div>
                  
                  <h4 className="mt-4 text-[17px] font-medium text-text">{step.subtitle}</h4>
                  <p className="mt-2 text-[12.5px] leading-[1.5] text-muted min-h-[40px]">{step.desc}</p>
                  
                  {/* Console Log Sub-panel */}
                  <div className="mt-4 rounded-lg bg-surface border border-border p-3 font-mono text-[10px] leading-relaxed text-muted min-h-[85px] flex flex-col justify-end">
                    <div className="mb-1 text-faint text-[9px] border-b pb-1 flex justify-between">
                      <span>AUDIT LOG</span>
                      <span className={isActive ? "text-amber" : ""}>{isActive ? "● RUNNING" : "● IDLE"}</span>
                    </div>
                    <AnimatePresence mode="popLayout">
                      {step.logs.map((log, lIdx) => (
                        <motion.div 
                          key={log}
                          initial={{ opacity: 0, x: -4 }}
                          animate={{ opacity: isActive ? 1 : 0.4, x: 0 }}
                          exit={{ opacity: 0 }}
                          transition={{ delay: lIdx * 0.15, duration: 0.2 }}
                          className="flex items-start gap-1 text-muted"
                        >
                          <span className="text-amber-soft select-none">&gt;</span>
                          <span className="truncate">{log}</span>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* Connecting Line Tracker */}
          <div className="hidden md:block absolute left-8 right-8 top-[36px] h-px bg-border/40 z-[1] pointer-events-none">
            <motion.div 
              className="h-full bg-amber shadow-[0_0_8px_rgba(217,138,59,0.6)]"
              animate={{ 
                left: `${(activeStep / 4) * 100}%`,
                width: "25%"
              }}
              transition={{ type: "spring", stiffness: 70, damping: 15 }}
              style={{ position: "absolute" }}
            />
          </div>
        </Card>
      </div>

      {/* Catalogue Preview Section */}
      <SectionLabel right={<Link href="/catalogue" className="font-mono text-xs text-muted hover:text-text flex items-center gap-1.5">View all features <ArrowRight size={12} /></Link>}>
        Catalogue Preview
      </SectionLabel>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-14">
        {features.filter(f => ["f23", "f13", "f25"].includes(f.id)).map((f) => (
          <Card key={f.id} className="p-5.5 flex flex-col justify-between min-h-[170px] hover:border-faint transition-colors">
            <div>
              <div className="flex items-start justify-between">
                <div>
                  <Link href={`/memo/${f.id}`} className="text-lg font-medium hover:text-amber transition-colors">
                    {f.name}
                  </Link>
                  <div className="text-xs text-faint font-mono mt-0.5">{f.area} · {money(f.annual_cost)} / yr</div>
                </div>
                <VerdictBadge verdict={f.verdict} reclassify={f.reclassify} />
              </div>
              <p className="text-[13px] text-muted mt-3.5 leading-relaxed">
                {f.id === "f23" && "Used by 0.8% of users representing 40% of ARR. Risk: $2.21M ARR contract block."}
                {f.id === "f13" && "Low usage but bound explicitly by MSA compliance terms for Vertex and Northwind."}
                {f.id === "f25" && "OAuth connection state bug caused 95% usage collapse. Engineering fix recommended."}
              </p>
            </div>
            
            <div className="mt-4 pt-3.5 border-t flex justify-between items-center text-xs text-faint">
              <span className="font-mono">Confidence: {f.confidence}</span>
              <Link href={`/memo/${f.id}`} className="text-text hover:text-amber font-mono flex items-center gap-1">
                Read Memo <ArrowRight size={11} />
              </Link>
            </div>
          </Card>
        ))}
      </div>

      {/* recent decisions */}
      <SectionLabel right={<Link href="/catalogue" className="font-mono text-xs text-muted hover:text-text">Full Catalogue →</Link>}>
        Recent audit evaluations
      </SectionLabel>
      <Card className="overflow-hidden mb-14">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b bg-surface-2/50">
                {["Feature", "Verdict", "Confidence", "Risk accounts", "Reviewed"].map((h) => (
                  <th key={h} className="px-5 py-3.5 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted border-0">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {features.slice(0, 5).map((f) => (
                <tr key={f.id} className="border-b last:border-0 hover:bg-surface-2/30 transition-colors">
                  <td className="px-5 py-4 border-0">
                    <Link href={`/memo/${f.id}`} className="font-medium hover:text-amber transition-colors">{f.name}</Link>
                    <span className="text-xs text-faint font-mono"> · {f.area}</span>
                  </td>
                  <td className="px-5 py-4 border-0"><VerdictBadge verdict={f.verdict} reclassify={f.reclassify} /></td>
                  <td className="px-5 py-4 border-0 font-mono text-xs text-muted capitalize">{f.confidence}</td>
                  <td className={`px-5 py-4 border-0 font-mono text-[13px] ${f.risk_accounts ? "text-amber" : "text-faint"}`}>{f.risk_accounts ?? "—"}</td>
                  <td className="px-5 py-4 border-0 font-mono text-xs text-muted">{f.reviewed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* metrics */}
      <SectionLabel right={<Link href="/scorecard" className="font-mono text-xs text-muted hover:text-text">Full scorecard →</Link>}>
        Accuracy metrics
      </SectionLabel>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
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


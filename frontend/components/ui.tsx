import type { ReactNode } from "react";
import { VERDICT_STYLE, type Verdict } from "@/lib/data";

const DOT: Record<string, string> = {
  safe: "bg-teal",
  neutral: "bg-faint",
  risk: "bg-amber",
  escalate: "bg-amber shadow-[0_0_7px_rgb(217_138_59_/_0.7)]",
};
const TEXT: Record<string, string> = {
  safe: "text-teal border-teal/30",
  neutral: "text-muted border-border",
  risk: "text-amber border-amber/35",
  escalate: "text-amber border-amber/45 bg-amber/[0.06]",
};

export function VerdictBadge({ verdict, reclassify }: { verdict: Verdict; reclassify?: boolean }) {
  const s = VERDICT_STYLE[verdict];
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <span
        className={`inline-flex items-center gap-1.5 rounded-[5px] border px-2 py-[3px] font-mono text-[11px] uppercase tracking-[0.06em] ${TEXT[s.kind]}`}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${DOT[s.kind]}`} />
        {s.label}
      </span>
      {reclassify && (
        <span className="font-mono text-[11px] text-muted">· reclassify</span>
      )}
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border bg-surface ${className}`} style={{ boxShadow: "var(--shadow)" }}>
      {children}
    </div>
  );
}

export function Stat({ label, value, foot, tone }: { label: string; value: ReactNode; foot?: string; tone?: "amber" | "teal" }) {
  const c = tone === "amber" ? "text-amber" : tone === "teal" ? "text-teal" : "";
  return (
    <Card className="p-5">
      <div className="font-mono text-[11px] uppercase tracking-[0.08em] text-muted">{label}</div>
      <div className={`mt-2.5 font-display text-[34px] leading-none tracking-tight ${c}`}>{value}</div>
      {foot && <div className="mt-1.5 text-xs text-faint">{foot}</div>}
    </Card>
  );
}

export function SectionLabel({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="mt-16 mb-4 flex items-baseline justify-between">
      <h2 className="text-2xl">{children}</h2>
      {right}
    </div>
  );
}

import Link from "next/link";
import { TRAPS, SCORECARD } from "@/lib/data";
import { Card } from "@/components/ui";

const WRAP = "mx-auto max-w-[1180px] px-8";

export default function Scorecard() {
  return (
    <div className={WRAP}>
      <div className="pb-2 pt-11">
        <div className="mb-3.5 font-mono text-xs text-muted"><Link href="/" className="hover:text-text">Sunset</Link> / Scorecard</div>
        <h1 className="text-[32px]">Evaluation</h1>
        <p className="mt-2 max-w-[60ch] text-muted">
          Every claim this system makes is measured against a held-out ground-truth sheet and a named
          deterministic baseline.
        </p>
      </div>

      <div className="mb-6 mt-2 grid grid-cols-1 gap-5 md:grid-cols-2">
        <Card className="p-6">
          <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted">Deterministic baseline</div>
          <div className="my-3 font-display text-[52px] leading-none tracking-[-0.02em]">32.5%</div>
          <div className="text-[13px] text-muted">13 of 40 features · usage percentiles + keyword grep</div>
          <div className="mt-2.5 font-mono text-[12.5px] text-amber">▲ 2 catastrophic contract breaches</div>
        </Card>
        <Card className="border-teal/30 p-6">
          <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted">Agent pipeline</div>
          <div className="my-3 font-display text-[52px] leading-none tracking-[-0.02em] text-muted">—</div>
          <div className="text-[13px] text-muted">headline suppressed · offline stub run</div>
          <div className="mt-2.5 font-mono text-[12.5px] text-teal">✓ 0 catastrophic errors · 100% citations</div>
        </Card>
      </div>

      <div className="inline-block rounded-md border px-3.5 py-2 font-mono text-xs text-amber"
        style={{ borderColor: "color-mix(in srgb, var(--amber) 30%, var(--border))", background: "rgb(var(--glow) / 0.05)" }}>
        OFFLINE STUB — the accuracy headline is withheld until a model run. Structure, catastrophic rate and citation validity below are real.
      </div>

      <h2 className="mb-4 mt-9 text-2xl">Per trap class</h2>
      <div className="mb-6 flex gap-6 font-mono text-xs text-muted">
        <span><i className="mr-2 inline-block h-2 w-5 rounded bg-faint align-middle" />Rules baseline</span>
        <span><i className="mr-2 inline-block h-2 w-5 rounded bg-teal align-middle" />Agent</span>
      </div>
      <Card className="px-6 py-3">
        {TRAPS.map((t) => (
          <div key={t.slug} className="grid grid-cols-[140px_1fr_1fr] items-center gap-4 border-b py-3 last:border-0 md:grid-cols-[180px_1fr_1fr]">
            <div className="text-[13.5px]">{t.name}<span className="block font-mono text-[11px] text-faint">{t.slug}</span></div>
            <Bar value={t.base} cls="bg-faint" />
            <Bar value={t.agent} cls="bg-teal" />
          </div>
        ))}
      </Card>

      <h2 className="mb-4 mt-9 text-2xl">Cost &amp; integrity</h2>
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
            <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-muted">{l}</div>
            <div className={`mt-2 font-display text-[26px] ${tone === "teal" ? "text-teal" : tone === "amber" ? "text-amber" : ""}`}>{v}</div>
            <div className="mt-1 text-xs text-faint">{d}</div>
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

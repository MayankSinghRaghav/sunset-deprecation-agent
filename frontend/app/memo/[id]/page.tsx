import Link from "next/link";
import { MEMO, money, VERDICT_STYLE } from "@/lib/data";
import { VerdictBadge } from "@/components/ui";

const WRAP = "mx-auto max-w-[1180px] px-8";

export default async function MemoPage({ params }: { params: Promise<{ id: string }> }) {
  await params;
  const m = MEMO;
  return (
    <>
      <div className={WRAP}>
        {/* hero */}
        <div className="border-b pb-8 pt-13" style={{ paddingTop: "3.25rem" }}>
          <div className="mb-5 font-mono text-xs text-muted">
            <Link href="/" className="hover:text-text">Sunset</Link> / <Link href="/catalogue" className="hover:text-text">Catalogue</Link> / {m.name}
          </div>
          <VerdictBadge verdict={m.verdict} reclassify={m.reclassify} />
          <h1 className="mt-4 max-w-[20ch] text-[clamp(30px,4.4vw,46px)]">{m.headline}</h1>
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
            {m.claims.map((c) => (
              <div key={c.who} className={`my-4 border-l-2 pl-[18px] ${c.amber ? "border-amber" : "border-border"}`}>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-faint">{c.who} auditor</div>
                <p className="mt-1.5 text-[15px] leading-[1.55]">{c.text}</p>
                <div className="mt-2.5 rounded-md border bg-surface px-3 py-2.5 font-mono text-xs leading-[1.5] text-muted">
                  <span className="text-amber-soft">{c.citation.id} · {c.citation.source}</span>
                  &nbsp;&nbsp;<span className="text-text">{c.citation.quote}</span>
                </div>
              </div>
            ))}

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
            <div id="recommendation" className="relative my-10 rounded-2xl border p-8"
              style={{ borderColor: "color-mix(in srgb, var(--amber) 34%, var(--border))", background: "linear-gradient(180deg, rgb(var(--glow) / 0.05), rgb(var(--glow) / 0.015))" }}>
              <div className="eyebrow" style={{ color: "var(--amber)" }}>{m.recommendation.eyebrow}</div>
              <h2 className="my-3 max-w-[22ch] text-[30px]">{m.recommendation.heading}</h2>
              <p className="max-w-[60ch] text-muted">{m.recommendation.body}</p>
              <div className="mt-5 flex flex-col gap-2">
                {m.at_risk.map((a) => (
                  <div key={a.name} className="flex items-center gap-3 rounded-lg border px-3.5 py-2.5"
                    style={{ borderColor: "color-mix(in srgb, var(--amber) 30%, var(--border))", background: "rgb(var(--glow) / 0.05)" }}>
                    <span className="text-sm font-medium">{a.name}</span>
                    <span className="font-mono text-[12.5px] text-amber">{a.why}</span>
                    <span className="ml-auto font-mono text-[13px] text-muted">{a.arr}</span>
                  </div>
                ))}
              </div>
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
          <aside className="lg:sticky lg:top-[84px]">
            <div className="rounded-2xl border bg-surface p-6" style={{ boxShadow: "var(--shadow)" }}>
              <div className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">Dissent · the other side</div>
              <h4 className="my-3.5 font-display text-[21px] italic leading-[1.3]">
                “If the replacement fully covers each account today, this is a clean removal — not a migration.”
              </h4>
              <p className="text-[14.5px] leading-[1.6]">{m.dissent}</p>
              <div className="my-[18px] h-px bg-border" />
              <Row k="Confidence" v={m.confidence} />
              <Row k="Applied rule" v={m.applied_rule} />
              <p className="mt-4 text-xs leading-[1.5] text-faint">
                This panel never collapses. A deprecation tool that only argues its own side is how you get
                a confident, wrong, expensive removal.
              </p>
            </div>
          </aside>
        </div>
      </div>
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

"use client";
import { useEffect, useRef } from "react";

// The signature: a fixed warm light that swells as the recommendation nears the
// centre of the viewport, then fades — cold daylight at the top, sunset at the
// decision, neutral again by the dissent. Respects prefers-reduced-motion.
export function SunsetGlow({ targetId }: { targetId: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      el.style.opacity = "0.22";
      return;
    }
    let raf = 0;
    const update = () => {
      raf = 0;
      const rec = document.getElementById(targetId);
      if (!rec) {
        el.style.opacity = "0";
        return;
      }
      const r = rec.getBoundingClientRect();
      const vh = window.innerHeight;
      const center = r.top + r.height / 2;
      const dist = Math.abs(center - vh * 0.52) / vh; // 0 when centred
      const warmth = Math.max(0, 1 - dist * 1.3);
      el.style.opacity = (warmth * 0.95).toFixed(3);
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [targetId]);

  return <div ref={ref} className="sun-glow" style={{ opacity: 0, transition: "opacity .45s ease" }} />;
}

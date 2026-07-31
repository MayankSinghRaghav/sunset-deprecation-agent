"use client";
import { useEffect } from "react";

// The signature. The whole interface travels from cold daylight at the top of a
// page into a warm sunset at the bottom: as you scroll, the body background
// interpolates cold → dusk and a sun rises from below the horizon. Warmth is
// driven by overall scroll progress, so it works on every screen; when a memo's
// #recommendation is on the page it gets an extra swell at the decision moment.
// Mounted once, globally. Sets the --warm custom property; CSS does the painting.
// Respects prefers-reduced-motion.
export function SunsetGlow() {
  useEffect(() => {
    const root = document.documentElement;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      root.style.setProperty("--warm", "0.4");
      return;
    }
    let raf = 0;
    const update = () => {
      raf = 0;
      const max = root.scrollHeight - window.innerHeight;
      let p = max > 4 ? window.scrollY / max : 0;
      p = Math.min(1, Math.max(0, p));
      let warmth = p * p * (3 - 2 * p); // smoothstep: crisp cold at the top

      const rec = document.getElementById("recommendation");
      if (rec) {
        const r = rec.getBoundingClientRect();
        const center = r.top + r.height / 2;
        const near = Math.max(0, 1 - Math.abs(center - window.innerHeight * 0.5) / window.innerHeight);
        warmth = Math.min(1, warmth + near * 0.35);
      }
      root.style.setProperty("--warm", warmth.toFixed(3));
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
      root.style.removeProperty("--warm");
    };
  }, []);

  return <div className="sun-glow" aria-hidden="true" />;
}

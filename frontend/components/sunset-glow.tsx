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
      const rec = document.getElementById("recommendation");
      let warmth = 0;

      if (rec) {
        // Feature Memo page specific scroll transitions
        const r = rec.getBoundingClientRect();
        const vh = window.innerHeight;
        const center = r.top + r.height / 2;
        const distance = Math.abs(center - vh * 0.5);
        const maxDistance = vh * 0.85; // Distance range where warmth is active

        if (distance < maxDistance) {
          const norm = distance / maxDistance; // 0 to 1
          // Cosine shape to make transition organic, peaking when recommendation is centered
          const shape = Math.cos(norm * Math.PI / 2);
          warmth = shape * shape; // Sharp fall-off
        }
      } else {
        // Other pages: Gentle ambient scroll glow, capped at 0.12 to keep interface clean
        const max = root.scrollHeight - window.innerHeight;
        const p = max > 4 ? window.scrollY / max : 0;
        warmth = Math.min(0.12, Math.max(0, p * 0.12));
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

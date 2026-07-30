"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

const LINKS = [
  { href: "/catalogue", label: "Catalogue" },
  { href: "/scorecard", label: "Scorecard" },
  { href: "/accounts", label: "Account Exposure" },
];

export function SiteNav() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b bg-bg/80 backdrop-blur-xl">
      <nav className="mx-auto flex h-[60px] max-w-[1180px] items-center gap-8 px-8">
        <Link href="/" className="flex items-center gap-2.5 font-display text-xl">
          <span className="h-[9px] w-[9px] rounded-full bg-amber shadow-[0_0_10px_1px_rgb(217_138_59_/_0.5)]" />
          Sunset
        </Link>
        <div className="ml-1 hidden gap-6 md:flex">
          {LINKS.map((l) => {
            const active = path.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`border-b-[1.5px] py-1 text-[13.5px] transition-colors ${
                  active ? "border-amber text-text" : "border-transparent text-muted hover:text-text"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </div>
        <div className="flex-1" />
        <ThemeToggle />
        <Link
          href="/catalogue"
          className="rounded-md border bg-surface px-3.5 py-2 text-[13px] font-medium transition-colors hover:border-faint"
        >
          Run Audit
        </Link>
      </nav>
    </header>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const dark = resolvedTheme === "dark";
  return (
    <button
      aria-label="Toggle theme"
      onClick={() => setTheme(dark ? "light" : "dark")}
      className="flex h-8 w-8 items-center justify-center rounded-md border bg-surface text-muted transition-colors hover:text-text"
    >
      {mounted && dark ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
}

import type { Metadata } from "next";
import { Newsreader, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { SiteNav } from "@/components/site-nav";
import { SunsetGlow } from "@/components/sunset-glow";
import { AppStoreProvider } from "@/lib/store";

const newsreader = Newsreader({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-newsreader", display: "swap" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const plex = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex", display: "swap" });

export const metadata: Metadata = {
  title: "Sunset — Product Operations",
  description: "Assembles the case for deprecating a software feature. A human signs the death warrant.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${newsreader.variable} ${inter.variable} ${plex.variable}`}>
      <body>
        <ThemeProvider>
          <AppStoreProvider>
            <SunsetGlow />
            <SiteNav />
            <main className="relative z-[1]">{children}</main>
            <SiteFooter />
          </AppStoreProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

function SiteFooter() {
  return (
    <footer className="relative z-[1] mt-20 border-t bg-surface-2/40 py-12">
      <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-4 px-8">
        <div>
          <div className="flex items-center gap-2.5 font-display text-lg">
            <span className="h-[9px] w-[9px] rounded-full bg-amber" />Sunset
          </div>
          <p className="mt-3 max-w-[52ch] text-[12.5px] text-faint">
            A governance tool for feature deprecation. It assembles the case; a human signs the death warrant.
          </p>
        </div>
        <p className="text-right font-mono text-xs text-faint">
          Product Operations<br />Evidence · Governance · Decision support
        </p>
      </div>
    </footer>
  );
}

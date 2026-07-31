"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { useAppStore } from "@/lib/store";
import { money, type Verdict } from "@/lib/data";
import { VerdictBadge, Card } from "@/components/ui";
import { Search, X, FileText, AlertCircle, RefreshCw } from "lucide-react";

const WRAP = "mx-auto max-w-[1180px] px-8";
const FILTERS: (Verdict | "ALL")[] = ["ALL", "MIGRATE", "ESCALATE", "FIX", "KILL", "KEEP"];

type SortField = "name" | "verdict" | "confidence" | "annual_cost" | "reviewed";
type SortOrder = "asc" | "desc";

export default function Catalogue() {
  const { features, triggerAudit, isAuditing } = useAppStore();
  const [q, setQ] = useState("");
  const [f, setF] = useState<Verdict | "ALL">("ALL");
  
  // Sorting State
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");

  // Selection State
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Filter, Search, and Sort features
  const filteredAndSortedRows = useMemo(() => {
    // 1. Filter and Search
    let result = features.filter(
      (r) => (f === "ALL" || r.verdict === f) && r.name.toLowerCase().includes(q.toLowerCase())
    );

    // 2. Sort
    result.sort((a, b) => {
      let valA: any = a[sortField];
      let valB: any = b[sortField];

      if (sortField === "verdict") {
        valA = a.verdict;
        valB = b.verdict;
      }

      if (typeof valA === "string") {
        return sortOrder === "asc" 
          ? valA.localeCompare(valB) 
          : valB.localeCompare(valA);
      } else {
        return sortOrder === "asc" 
          ? (valA as number) - (valB as number) 
          : (valB as number) - (valA as number);
      }
    });

    return result;
  }, [features, q, f, sortField, sortOrder]);

  // Bulk Selection Handlers
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(filteredAndSortedRows.map((r) => r.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectRow = (id: string, checked: boolean) => {
    if (checked) {
      setSelectedIds((prev) => [...prev, id]);
    } else {
      setSelectedIds((prev) => prev.filter((item) => item !== id));
    }
  };

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  const isAllSelected = 
    filteredAndSortedRows.length > 0 && 
    filteredAndSortedRows.every((r) => selectedIds.includes(r.id));

  // Action feedback simulators
  const handleBulkAction = (actionName: string) => {
    alert(`Bulk Action: "${actionName}" triggered for features: ${selectedIds.join(", ")}`);
    setSelectedIds([]);
  };

  return (
    <div className={`${WRAP} pb-24 relative`}>
      <div className="pb-2 pt-11">
        <div className="mb-3.5 font-mono text-xs text-muted">
          <Link href="/" className="hover:text-text">Sunset</Link> / Catalogue
        </div>
        <h1 className="text-[32px]">Feature catalogue</h1>
      </div>

      <div className="my-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex max-w-[340px] flex-1 items-center gap-2.5 rounded-lg border bg-surface px-3.5 py-2.5">
            <Search size={15} className="text-faint" />
            <input 
              value={q} 
              onChange={(e) => setQ(e.target.value)} 
              placeholder="Search features…"
              className="w-full bg-transparent text-[13px] outline-none placeholder:text-faint" 
            />
            {q && (
              <button onClick={() => setQ("")} className="text-faint hover:text-text">
                <X size={14} />
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((v) => (
              <button 
                key={v} 
                onClick={() => setF(v)}
                className={`rounded-full border px-3.5 py-1.5 font-mono text-xs transition-colors ${
                  f === v ? "border-amber/55 bg-amber/[0.04] text-text" : "text-muted hover:text-text"
                }`}
              >
                {v === "ALL" ? "All" : v.charAt(0) + v.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={triggerAudit}
          disabled={isAuditing}
          className="rounded-md border bg-surface hover:bg-surface-2/40 border-border px-4 py-2 text-[13px] font-medium text-text transition-colors flex items-center gap-2"
        >
          <RefreshCw size={13} className={isAuditing ? "animate-spin" : ""} />
          {isAuditing ? "Auditing..." : "Audit Catalogue"}
        </button>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b bg-surface-2/40">
                <th className="px-4 py-3.5 text-left w-10">
                  <input 
                    type="checkbox" 
                    checked={isAllSelected}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="accent-amber h-3.5 w-3.5 rounded border-border"
                  />
                </th>
                <th 
                  onClick={() => toggleSort("name")}
                  className="cursor-pointer px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted select-none hover:text-text"
                >
                  <div className="flex items-center gap-1.5">
                    Feature {sortField === "name" && (sortOrder === "asc" ? "▲" : "▼")}
                  </div>
                </th>
                <th 
                  onClick={() => toggleSort("verdict")}
                  className="cursor-pointer px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted select-none hover:text-text"
                >
                  <div className="flex items-center gap-1.5">
                    Verdict {sortField === "verdict" && (sortOrder === "asc" ? "▲" : "▼")}
                  </div>
                </th>
                <th 
                  onClick={() => toggleSort("confidence")}
                  className="cursor-pointer px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted select-none hover:text-text"
                >
                  <div className="flex items-center gap-1.5">
                    Confidence {sortField === "confidence" && (sortOrder === "asc" ? "▲" : "▼")}
                  </div>
                </th>
                <th 
                  onClick={() => toggleSort("annual_cost")}
                  className="cursor-pointer px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted select-none hover:text-text"
                >
                  <div className="flex items-center gap-1.5">
                    Annual cost {sortField === "annual_cost" && (sortOrder === "asc" ? "▲" : "▼")}
                  </div>
                </th>
                <th className="px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted">Risk accounts</th>
                <th 
                  onClick={() => toggleSort("reviewed")}
                  className="cursor-pointer px-4 py-3 text-left font-mono text-[10.5px] font-normal uppercase tracking-[0.1em] text-muted select-none hover:text-text"
                >
                  <div className="flex items-center gap-1.5">
                    Reviewed {sortField === "reviewed" && (sortOrder === "asc" ? "▲" : "▼")}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedRows.map((r) => {
                const isSelected = selectedIds.includes(r.id);
                return (
                  <tr 
                    key={r.id} 
                    className={`border-b transition-colors last:border-0 hover:bg-surface-2/40 ${
                      isSelected ? "bg-amber/[0.01]" : ""
                    }`}
                  >
                    <td className="px-4 py-3.5">
                      <input 
                        type="checkbox" 
                        checked={isSelected}
                        onChange={(e) => handleSelectRow(r.id, e.target.checked)}
                        className="accent-amber h-3.5 w-3.5 rounded border-border"
                      />
                    </td>
                    <td className="px-4 py-3.5">
                      <Link href={`/memo/${r.id}`} className="font-medium hover:text-amber transition-colors">{r.name}</Link>
                      <span className="text-xs text-faint font-mono"> · {r.area}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <VerdictBadge verdict={r.verdict} reclassify={r.reclassify} />
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs capitalize text-muted">{r.confidence}</td>
                    <td className="px-4 py-3.5 font-mono text-[13px] text-muted">{money(r.annual_cost)}</td>
                    <td className={`px-4 py-3.5 font-mono text-[13px] ${r.risk_accounts ? "text-amber" : "text-faint"}`}>
                      {r.risk_accounts ?? "—"}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-muted">{r.reviewed}</td>
                  </tr>
                );
              })}
              {filteredAndSortedRows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-16 text-center text-sm text-muted">
                    No features match the criteria. Clear filters or search string to see all.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Floating Bulk Action Drawer */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 bg-surface border border-amber/35 px-5 py-3.5 rounded-full shadow-[0_12px_32px_rgba(0,0,0,0.45)] text-[13px] max-w-lg w-[calc(100%-2rem)] backdrop-blur-xl animate-[slideUp_0.2s_ease-out]">
          <div className="flex items-center gap-2 font-mono font-medium whitespace-nowrap text-text">
            <span className="h-2 w-2 rounded-full bg-amber animate-pulse" />
            {selectedIds.length} Selected
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="flex gap-2.5 overflow-x-auto select-none no-scrollbar">
            <button 
              onClick={() => handleBulkAction("Export Cited Case Files")}
              className="flex items-center gap-1.5 hover:text-text text-muted transition-colors font-medium whitespace-nowrap cursor-pointer"
            >
              <FileText size={13} /> Export Case
            </button>
            <button 
              onClick={() => handleBulkAction("Flag for Legal Review")}
              className="flex items-center gap-1.5 hover:text-text text-muted transition-colors font-medium whitespace-nowrap cursor-pointer"
            >
              <AlertCircle size={13} /> Legal Review
            </button>
            <button 
              onClick={() => handleBulkAction("Re-run Auditors")}
              className="flex items-center gap-1.5 hover:text-text text-amber-soft transition-colors font-medium whitespace-nowrap cursor-pointer"
            >
              <RefreshCw size={13} /> Re-run
            </button>
          </div>
          <div className="h-4 w-px bg-border" />
          <button 
            onClick={() => setSelectedIds([])} 
            className="text-faint hover:text-text transition-colors p-1 cursor-pointer"
            title="Deselect All"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

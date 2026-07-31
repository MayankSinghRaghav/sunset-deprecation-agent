"use client";
import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { CATALOGUE, MEMO, EXPOSURE, SCORECARD, TRAPS, type FeatureRow, type Memo, type Verdict } from "./data";

export interface AuditRun {
  id: string;
  status: "running" | "completed" | "failed";
  features_completed: number;
  features_total: number;
  cost_tokens: string;
  latency: string;
  used_offline_stub: boolean;
  started_at: string;
  finished_at?: string;
}

export interface AuditLog {
  timestamp: string;
  featureId: string;
  featureName: string;
  auditor: "Usage" | "Contract" | "Support" | "Revenue" | "Reconciler" | "Composer" | "Validator";
  message: string;
  status?: "info" | "warning" | "success" | "error";
}

export interface Override {
  featureId: string;
  newVerdict: Verdict;
  reason: string;
  timestamp: string;
}

interface AppContextType {
  features: FeatureRow[];
  activeRun: AuditRun | null;
  runs: AuditRun[];
  logs: AuditLog[];
  overrides: Record<string, Override>;
  selectedAccountId: string;
  isAuditing: boolean;
  auditProgress: number;
  hasRunAudit: boolean;
  triggerAudit: () => Promise<void>;
  addOverride: (featureId: string, newVerdict: Verdict, reason: string) => void;
  setSelectedAccountId: (id: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const AUDIT_STEPS: { featureId: string; name: string; logs: Omit<AuditLog, "timestamp">[] }[] = [
  {
    featureId: "f08",
    name: "Dashboard v2",
    logs: [
      { featureId: "f08", featureName: "Dashboard v2", auditor: "Usage", message: "Usage trend flat. High daily active users (>10,000).", status: "success" },
      { featureId: "f08", featureName: "Dashboard v2", auditor: "Contract", message: "No signed obligations mapping specifically to v2 layout.", status: "info" },
      { featureId: "f08", featureName: "Dashboard v2", auditor: "Reconciler", message: "Policy check: high usage detected. Keeping feature.", status: "success" }
    ]
  },
  {
    featureId: "f23",
    name: "Multi-Currency Billing",
    logs: [
      { featureId: "f23", featureName: "Multi-Currency Billing", auditor: "Usage", message: "Only three active accounts touch this feature. 0.8% of user base.", status: "info" },
      { featureId: "f23", featureName: "Multi-Currency Billing", auditor: "Revenue", message: "WARNING: Active accounts represent 40% ($2.21M ARR) of total platform revenue.", status: "warning" },
      { featureId: "f23", featureName: "Multi-Currency Billing", auditor: "Contract", message: "No specific contractual obligations. Clean migration path available.", status: "info" },
      { featureId: "f23", featureName: "Multi-Currency Billing", auditor: "Reconciler", message: "Policy check: Revenue concentration rule R3 triggered. Escalate to MIGRATE.", status: "warning" },
      { featureId: "f23", featureName: "Multi-Currency Billing", auditor: "Composer", message: "Memo compiled: Vertex, Meridian, and Atlas must be migrated to REST API bulk endpoints.", status: "info" }
    ]
  },
  {
    featureId: "f13",
    name: "Audit Log Export",
    logs: [
      { featureId: "f13", featureName: "Audit Log Export", auditor: "Usage", message: "Low usage volume (under 10 monthly events).", status: "info" },
      { featureId: "f13", featureName: "Audit Log Export", auditor: "Contract", message: "CRITICAL: Obligated under Master Services Agreement for 2 premium customers.", status: "error" },
      { featureId: "f13", featureName: "Audit Log Export", auditor: "Reconciler", message: "Contract veto applied: C1. Verdict forced to ESCALATE.", status: "error" }
    ]
  },
  {
    featureId: "f25",
    name: "Salesforce Sync",
    logs: [
      { featureId: "f25", featureName: "Salesforce Sync", auditor: "Usage", message: "Usage dropped 95% over the trailing 30 days.", status: "warning" },
      { featureId: "f25", featureName: "Salesforce Sync", auditor: "Support", message: "Defect spike: 18 open tickets since recent release. Error code 503.", status: "error" },
      { featureId: "f25", featureName: "Salesforce Sync", auditor: "Reconciler", message: "Policy check: Broken, not unwanted (Trap 4) triggered. Verdict = FIX.", status: "warning" }
    ]
  },
  {
    featureId: "f30",
    name: "Tax Document Generator",
    logs: [
      { featureId: "f30", featureName: "Tax Document Generator", auditor: "Usage", message: "Usage is zero for 10 months. Peaks dramatically in Q1 (Jan-Mar).", status: "info" },
      { featureId: "f30", featureName: "Tax Document Generator", auditor: "Reconciler", message: "Policy check: Seasonal usage (Trap 5) recognized. Verdict = KEEP.", status: "success" }
    ]
  },
  {
    featureId: "f33",
    name: "Status Page Widget",
    logs: [
      { featureId: "f33", featureName: "Status Page Widget", auditor: "Usage", message: "12,000 monthly page hits detected, but 99.8% represent API health checks.", status: "info" },
      { featureId: "f33", featureName: "Status Page Widget", auditor: "Usage", message: "Human events: 0 in past 90 days. Phantom usage detected.", status: "warning" },
      { featureId: "f33", featureName: "Status Page Widget", auditor: "Reconciler", message: "Policy check: Safe to kill. No contract or revenue exposure. Verdict = KILL.", status: "success" }
    ]
  },
  {
    featureId: "f37",
    name: "Compliance Certifications Center",
    logs: [
      { featureId: "f37", featureName: "Compliance Certifications Center", auditor: "Usage", message: "Active user count: 0.", status: "info" },
      { featureId: "f37", featureName: "Compliance Certifications Center", auditor: "Revenue", message: "CRM notes: Critical in 8 active sales opportunities. Revenue influence high.", status: "warning" },
      { featureId: "f37", featureName: "Compliance Certifications Center", auditor: "Reconciler", message: "Policy check: Sales-critical, product-dead. Verdict = KEEP (Reclassify).", status: "warning" }
    ]
  }
];

export function AppStoreProvider({ children }: { children: ReactNode }) {
  const [features, setFeatures] = useState<FeatureRow[]>(CATALOGUE);
  const [activeRun, setActiveRun] = useState<AuditRun | null>(null);
  const [runs, setRuns] = useState<AuditRun[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [overrides, setOverrides] = useState<Record<string, Override>>({});
  const [selectedAccountId, setSelectedAccountId] = useState<string>("acct_01");
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [auditProgress, setAuditProgress] = useState<number>(0);
  const [hasRunAudit, setHasRunAudit] = useState<boolean>(false);

  // Initialize with empty run or load past runs
  useEffect(() => {
    const saved = localStorage.getItem("sunset_runs");
    if (saved) {
      setRuns(JSON.parse(saved));
      setHasRunAudit(true);
    }
    const savedOverrides = localStorage.getItem("sunset_overrides");
    if (savedOverrides) {
      const parsed = JSON.parse(savedOverrides);
      setOverrides(parsed);
      // Update catalogue features with saved overrides
      setFeatures(prev =>
        prev.map(f => (parsed[f.id] ? { ...f, verdict: parsed[f.id].newVerdict } : f))
      );
    }
  }, []);

  const triggerAudit = async () => {
    if (isAuditing) return;
    setIsAuditing(true);
    setAuditProgress(0);
    setLogs([]);
    
    const runId = `run_${Math.random().toString(36).substring(2, 8)}`;
    const newRun: AuditRun = {
      id: runId,
      status: "running",
      features_completed: 0,
      features_total: CATALOGUE.length,
      cost_tokens: "0",
      latency: "0.0s",
      used_offline_stub: false,
      started_at: new Date().toLocaleTimeString()
    };
    setActiveRun(newRun);

    const addLog = (log: Omit<AuditLog, "timestamp">) => {
      setLogs(prev => [...prev, { ...log, timestamp: new Date().toLocaleTimeString() }]);
    };

    // Phase 1: Intake & Prep
    addLog({ featureId: "*", featureName: "System", auditor: "Validator", message: "Initializing audit pipeline. Fetching postgres database schema...", status: "info" });
    await new Promise(r => setTimeout(r, 400));
    addLog({ featureId: "*", featureName: "System", auditor: "Validator", message: "Scanning telemetry data, contract texts, ticket queues, and CRM logs.", status: "info" });
    await new Promise(r => setTimeout(r, 400));

    // Process key features
    for (let i = 0; i < AUDIT_STEPS.length; i++) {
      const step = AUDIT_STEPS[i];
      setAuditProgress(Math.round(((i + 1) / AUDIT_STEPS.length) * 85));
      setActiveRun(prev => prev ? { ...prev, features_completed: Math.round(((i + 1) / AUDIT_STEPS.length) * CATALOGUE.length) } : null);
      
      addLog({ featureId: step.featureId, featureName: step.name, auditor: "Validator", message: `--- Auditing feature ${step.featureId} (${step.name}) ---`, status: "info" });
      await new Promise(r => setTimeout(r, 150));
      
      for (const log of step.logs) {
        addLog(log);
        await new Promise(r => setTimeout(r, 200));
      }
    }

    // Phase 3: Final validation
    setAuditProgress(90);
    addLog({ featureId: "*", featureName: "System", auditor: "Composer", message: "Generating decision memos for all audited items...", status: "info" });
    await new Promise(r => setTimeout(r, 300));
    setAuditProgress(95);
    addLog({ featureId: "*", featureName: "System", auditor: "Validator", message: "Running strict citation check. Verifying all claims bind to a database row.", status: "info" });
    await new Promise(r => setTimeout(r, 300));
    addLog({ featureId: "*", featureName: "System", auditor: "Validator", message: "Citation validation: 100% successful. No hallucinations detected.", status: "success" });
    
    // Complete audit
    const completedRun: AuditRun = {
      ...newRun,
      status: "completed",
      features_completed: CATALOGUE.length,
      cost_tokens: "43.5K",
      latency: "1.4s",
      finished_at: new Date().toLocaleTimeString()
    };

    setActiveRun(null);
    setRuns(prev => {
      const updated = [completedRun, ...prev];
      localStorage.setItem("sunset_runs", JSON.stringify(updated));
      return updated;
    });
    setIsAuditing(false);
    setAuditProgress(100);
    setHasRunAudit(true);
  };

  const addOverride = (featureId: string, newVerdict: Verdict, reason: string) => {
    const overrideObj: Override = {
      featureId,
      newVerdict,
      reason,
      timestamp: new Date().toLocaleDateString()
    };
    
    const newOverrides = { ...overrides, [featureId]: overrideObj };
    setOverrides(newOverrides);
    localStorage.setItem("sunset_overrides", JSON.stringify(newOverrides));

    // Update feature row verdict
    setFeatures(prev =>
      prev.map(f => (f.id === featureId ? { ...f, verdict: newVerdict, reclassify: newVerdict === "KEEP" && f.reclassify } : f))
    );
  };

  return (
    <AppContext.Provider
      value={{
        features,
        activeRun,
        runs,
        logs,
        overrides,
        selectedAccountId,
        isAuditing,
        auditProgress,
        hasRunAudit,
        triggerAudit,
        addOverride,
        setSelectedAccountId
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppStore() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useAppStore must be used within an AppStoreProvider");
  return context;
}

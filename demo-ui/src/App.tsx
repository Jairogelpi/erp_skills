import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { ApprovalPanel } from "./components/ApprovalPanel";
import { AuditComparisonTable, AuditTimeline } from "./components/AuditTimeline";
import { ErpStatePanel } from "./components/ErpStatePanel";
import { EvidencePanel } from "./components/EvidencePanel";
import {
  CapabilityMatrix,
  ParaphrasePanel,
} from "./components/ExperimentScorecard";
import { Header, RequestComposer } from "./components/Header";
import { SafetyPanel } from "./components/SafetyPanel";
import { SystemCard } from "./components/SystemCard";
import type {
  ApprovalGrant,
  AuditComparison,
  DemoRun,
  Evidence,
  ParaphraseResult,
  Preset,
  SystemName,
  TimelineEvent,
} from "./types/demo";

type Tab = "live" | "evidence";

export default function App() {
  const [tab, setTab] = useState<Tab>("live");
  const [presets, setPresets] = useState<Preset[]>([]);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);

  const [scenario, setScenario] = useState("approval");
  const [text, setText] = useState("");
  const [run, setRun] = useState<DemoRun | null>(null);
  const [grant, setGrant] = useState<ApprovalGrant | null>(null);
  const [audit, setAudit] = useState<AuditComparison | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [paraphrases, setParaphrases] = useState<ParaphraseResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.presets().then((loaded) => {
      setPresets(loaded);
      const initial = loaded.find((p) => p.id === "approval") ?? loaded[0];
      if (initial) {
        setScenario(initial.id);
        setText(initial.request_text);
      }
    });
    api
      .evidence()
      .then(setEvidence)
      .catch((exc: Error) => setEvidenceError(exc.message));
  }, []);

  const refreshSidePanels = useCallback(async (requestId: string) => {
    const [auditData, timelineData] = await Promise.all([
      api.audit(requestId),
      api.timeline(requestId),
    ]);
    setAudit(auditData);
    setTimeline(timelineData.events);
  }, []);

  const selectPreset = (id: string) => {
    const preset = presets.find((p) => p.id === id);
    setScenario(id);
    if (preset) setText(preset.request_text);
  };

  const doRun = async () => {
    setBusy(true);
    setError(null);
    setGrant(null);
    setParaphrases(null);
    try {
      const result = await api.run(scenario, text);
      setRun(result);
      await refreshSidePanels(result.request_id);
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doApprove = async () => {
    if (!run) return;
    setBusy(true);
    try {
      setGrant(await api.approve(run.request_id, "Demo Administrator"));
      await refreshSidePanels(run.request_id);
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doRerun = async () => {
    if (!run) return;
    setBusy(true);
    try {
      const result = await api.rerun(run.request_id);
      setRun(result);
      await refreshSidePanels(result.request_id);
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doParaphrases = async () => {
    if (!run) return;
    setBusy(true);
    try {
      setParaphrases(await api.paraphrases(run.request_id));
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app">
      <Header evidence={evidence} />

      <nav className="tabs">
        <button
          className={`tab ${tab === "live" ? "active" : ""}`}
          onClick={() => setTab("live")}
        >
          Live comparison
        </button>
        <button
          className={`tab ${tab === "evidence" ? "active" : ""}`}
          onClick={() => setTab("evidence")}
        >
          Experimental evidence
        </button>
      </nav>

      <main className="main">
        {evidenceError && (
          <section className="panel">
            <div className="error">
              Confirmatory evidence unavailable: {evidenceError}. No statistics
              are shown rather than placeholder ones.
            </div>
          </section>
        )}

        {tab === "live" && (
          <>
            <RequestComposer
              presets={presets}
              activePreset={scenario}
              text={text}
              busy={busy}
              onSelectPreset={selectPreset}
              onChangeText={setText}
              onRun={doRun}
            />

            {error && (
              <section className="panel">
                <div className="error">{error}</div>
              </section>
            )}

            {run && (
              <>
                <div className="systems">
                  {(["A", "B", "C"] as SystemName[]).map((name) => (
                    <SystemCard key={name} result={run.systems[name]} />
                  ))}
                </div>

                <ErpStatePanel systems={run.systems} />

                <ApprovalPanel
                  governed={run.systems.C}
                  grant={grant}
                  onApprove={doApprove}
                  onRerun={doRerun}
                  busy={busy}
                />

                <div className="composer-row" style={{ padding: "0 2px" }}>
                  <button onClick={doParaphrases} disabled={busy || !run}>
                    Test paraphrases
                  </button>
                </div>

                {paraphrases && (
                  <ParaphrasePanel result={paraphrases} evidence={evidence} />
                )}

                {scenario === "security" && evidence && (
                  <SafetyPanel evidence={evidence} />
                )}

                <div className="split">
                  <AuditTimeline events={timeline} />
                  {audit && (
                    <AuditComparisonTable comparison={audit} evidence={evidence} />
                  )}
                </div>
              </>
            )}
          </>
        )}

        {tab === "evidence" && evidence && (
          <>
            <EvidencePanel evidence={evidence} />
            <CapabilityMatrix evidence={evidence} />
            <SafetyPanel evidence={evidence} />
          </>
        )}
      </main>

      {/* Permanent, never conditional. */}
      <footer className="footer">
        <span>
          Demo behavior is illustrative. Statistical claims come from the frozen
          v2.1.2 confirmatory campaign.
        </span>
        <span>
          {evidence
            ? `${evidence.protocol_tag} · commit ${evidence.frozen_commit.slice(0, 12)}`
            : ""}
        </span>
      </footer>
    </div>
  );
}

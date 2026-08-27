import { useState } from "react";
import { api } from "../api/client";
import type { OperationResult } from "../types/demo";

/** Home / Live Operations (SPEC v2 §6): one text box, run against the
 * REAL governed pipeline (retrieval -> risk -> policy -> Odoo -> reread).
 * 503 when ODOO_URL/OPENROUTER_API_KEY are not set -- that is reported
 * honestly, not hidden behind a fallback to FakeERP (see "A/B/C
 * Comparison" tab for the reproducible backend). */
export function Operations() {
  const [text, setText] = useState(
    "Crea una oportunidad para Hotel Miramar con un importe esperado de 4000 euros.",
  );
  const [role] = useState("erp_user");
  const [result, setResult] = useState<OperationResult | null>(null);
  const [notConfigured, setNotConfigured] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setError(null);
    setNotConfigured(null);
    try {
      setResult(await api.runOperation(text, role));
    } catch (exc) {
      const message = (exc as Error).message;
      if (message.startsWith("503")) setNotConfigured(message);
      else setError(message);
    } finally {
      setBusy(false);
    }
  };

  const grantAndRerun = async () => {
    if (!result?.selected_skill_id) return;
    setBusy(true);
    try {
      await api.grantExecutionApproval(result.selected_skill_id);
      await run();
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="panel">
        <div className="panel-title">LIVE ODOO 19 — DEVELOPMENT INSTANCE</div>
        <div className="composer">
          <label>What do you want to do in the ERP?</label>
          <textarea value={text} onChange={(e) => setText(e.target.value)} />
          <div className="composer-row">
            <button className="primary" onClick={run} disabled={busy}>
              Run
            </button>
          </div>
        </div>
      </section>

      {notConfigured && (
        <section className="panel">
          <div className="note">
            Live Odoo is not configured on this machine ({notConfigured}). Set
            ODOO_URL / ODOO_DB / ODOO_API_KEY and OPENROUTER_API_KEY, or use the
            "A/B/C Comparison" tab, which runs against the reproducible FakeERP
            backend with no external dependency.
          </div>
        </section>
      )}
      {error && (
        <section className="panel">
          <div className="error">{error}</div>
        </section>
      )}

      {result && (
        <section className="panel">
          <div className="panel-title">Intent | Retrieved Skill | Risk | Policy</div>
          <div style={{ padding: "10px 16px 16px" }}>
            <div className="row">
              <span className="k">Decision</span>
              <span
                className={`v ${result.decision === "ALLOW" ? "ok" : ""}`}
              >
                {result.decision}
              </span>
            </div>
            <div className="row">
              <span className="k">Retrieved skill</span>
              <span className="v">{result.selected_skill_id ?? "—"}</span>
            </div>
            {result.candidates.length > 0 && (
              <div className="row">
                <span className="k">Candidates</span>
                <span className="v">
                  {result.candidates
                    .map((c) => `${c.skill_id} (${c.score})`)
                    .join(", ")}
                </span>
              </div>
            )}
            {result.reasons.length > 0 && (
              <div className="row">
                <span className="k">Reasons</span>
                <span className="v">{result.reasons.join("; ")}</span>
              </div>
            )}
            {result.note && (
              <div className="row">
                <span className="k">Note</span>
                <span className="v">{result.note}</span>
              </div>
            )}

            {result.decision === "REQUIRE_APPROVAL" && (
              <div className="composer-row">
                <button className="approve" onClick={grantAndRerun} disabled={busy}>
                  Approve & execute
                </button>
              </div>
            )}

            {result.execution && (
              <>
                <div className="row">
                  <span className="k">Execution</span>
                  <span className="v">
                    {result.execution.handler_error ? "ERROR" : "SUCCESS"}
                  </span>
                </div>
                {result.execution.output != null && (
                  <div className="row">
                    <span className="k">ID del registro (para el siguiente paso)</span>
                    <span
                      className="v mono"
                      style={{ fontSize: 16, fontWeight: 700, color: "var(--allow)" }}
                    >
                      {String(result.execution.output)}
                    </span>
                  </div>
                )}
              </>
            )}
            {result.independent_reread && (
              <div className="erp-box" style={{ marginTop: 10 }}>
                <div className="verified">Verified by independent Odoo reread</div>
                <pre style={{ margin: "6px 0 0" }}>
                  {JSON.stringify(result.independent_reread, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </section>
      )}
    </>
  );
}

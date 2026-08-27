import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ApprovalRow, AuditRow } from "../types/demo";

/** Approval Center (SPEC v2 §10): two kinds, never merged into one
 * meaning — "this ERP write may proceed" is not "this skill may enter
 * production". */
export function ApprovalsCenter() {
  const [rows, setRows] = useState<ApprovalRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.productApprovals().then(setRows).catch((e: Error) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  return (
    <section className="panel">
      <div className="panel-title">Approval Center</div>
      {error && <div className="error">{error}</div>}
      <div className="composer-row" style={{ padding: "0 16px" }}>
        <button onClick={load}>Refresh</button>
      </div>
      {rows.length === 0 && <div className="note">No approvals recorded yet.</div>}
      {rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Kind</th>
              <th>Actor</th>
              <th>Scope</th>
              <th>Granted at</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>
                  <span
                    className={`pill ${r.kind === "erp_execution" ? "hold" : "allow"}`}
                  >
                    {r.kind === "erp_execution"
                      ? "ERP EXECUTION APPROVAL"
                      : "SKILL ACTIVATION APPROVAL"}
                  </span>
                </td>
                <td>{r.actor}</td>
                <td className="mono">{r.scope}</td>
                <td className="mono">{r.granted_at}</td>
                <td>{r.to_state ?? "granted"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/** Audit Center (SPEC v2 §11): ERP execution requests and skill evolution
 * events, merged into one reconstructible timeline. */
export function AuditCenter() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.productAudit().then(setRows).catch((e: Error) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  return (
    <section className="panel">
      <div className="panel-title">Audit Center</div>
      {error && <div className="error">{error}</div>}
      <div className="composer-row" style={{ padding: "0 16px" }}>
        <button onClick={load}>Refresh</button>
      </div>
      {rows.length === 0 && <div className="note">No audit events recorded yet.</div>}
      {rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Kind</th>
              <th>Skill</th>
              <th>Decision / Transition</th>
              <th>Actor</th>
              <th>Recorded at</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>
                  <span
                    className={`pill ${r.kind === "erp_request" ? "hold" : "allow"}`}
                  >
                    {r.kind === "erp_request" ? "ERP REQUEST" : "SKILL EVOLUTION"}
                  </span>
                </td>
                <td className="mono">{r.skill_id ?? "—"}</td>
                <td>
                  {r.kind === "erp_request"
                    ? r.decision
                    : `${r.from_state} → ${r.to_state}`}
                </td>
                <td>{r.actor ?? "—"}</td>
                <td className="mono">{r.recorded_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

import type {
  AuditComparison,
  Evidence,
  SystemName,
  TimelineEvent,
} from "../types/demo";

const FACT_LABELS: Record<string, string> = {
  request_and_case_identity: "Request identity",
  intent_and_arguments: "Intent + arguments",
  selected_action_or_skill: "Capability",
  policy_permission_decision: "Policy + role",
  exact_tool_skill_handler_version: "Version + handler",
  result_and_observed_effects: "Outcome + effects",
  verification_approval_or_block_evidence: "Verification evidence",
};

export function AuditTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <section className="panel">
      <div className="panel-title">Audit trail</div>
      <div className="timeline">
        {events.map((event, index) => (
          <div className="tl-row" key={`${event.at}-${index}`}>
            <span className="at">{event.at}</span>
            <span>{event.label}</span>
            <span className="detail">{event.detail ?? ""}</span>
          </div>
        ))}
        {events.length === 0 && <div className="detail">No events yet.</div>}
      </div>
    </section>
  );
}

/**
 * The seven reconstruction facts of H7's rubric, scored per system by
 * the same `audit_reconstruction.reconstruct` the campaign used.
 *
 * The confirmatory figure underneath is loaded from the report, and the
 * caption keeps the two apart on purpose: this table is one request,
 * H7's number is 1,192 scenarios.
 */
export function AuditComparisonTable({
  comparison,
  evidence,
}: {
  comparison: AuditComparison;
  evidence: Evidence | null;
}) {
  const h7 = evidence?.cards.find((c) => c.key === "h7") ?? null;

  return (
    <section className="panel">
      <div className="panel-title">Audit reconstruction — this request</div>
      <div style={{ padding: "10px 16px 4px" }}>
        <table>
          <thead>
            <tr>
              <th>Fact</th>
              <th className="mono">A</th>
              <th className="mono">B</th>
              <th className="mono">C</th>
            </tr>
          </thead>
          <tbody>
            {comparison.fact_names.map((fact) => (
              <tr key={fact}>
                <td>{FACT_LABELS[fact] ?? fact}</td>
                {(["A", "B", "C"] as SystemName[]).map((system) => (
                  <td key={system} className="mono">
                    <span className={comparison.rows[system][fact] ? "ok" : "no"}>
                      {comparison.rows[system][fact] ? "✓" : "✗"}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
            <tr>
              <td style={{ color: "var(--muted)" }}>Coverage</td>
              {(["A", "B", "C"] as SystemName[]).map((system) => (
                <td key={system} className="mono">
                  {(comparison.coverage[system] * 100).toFixed(0)}%
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
      {h7 && (
        <div className="note">
          <strong>Confirmatory H7</strong> — C − A ={" "}
          {((h7.estimate ?? 0) * 100).toFixed(1)} pp, n ={" "}
          {h7.n?.toLocaleString()} scenarios, {h7.test}.{" "}
          {h7.supported ? "Supported." : "Not supported."} The table above is a
          single request; that figure is the frozen campaign.
        </div>
      )}
    </section>
  );
}

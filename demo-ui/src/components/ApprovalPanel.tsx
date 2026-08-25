import type { ApprovalGrant, DemoSystemResult } from "../types/demo";

/**
 * The approval gate, and the proof that it is a gate rather than a wall.
 *
 * Before approval the panel shows the ERP re-read that proves nothing
 * moved; after approval it shows the same request going through. Both
 * halves are needed: "nothing was mutated" is only meaningful next to a
 * demonstration that the write was possible all along.
 */
export function ApprovalPanel({
  governed,
  grant,
  onApprove,
  onRerun,
  busy,
}: {
  governed: DemoSystemResult;
  grant: ApprovalGrant | null;
  onApprove: () => void;
  onRerun: () => void;
  busy: boolean;
}) {
  const pending = governed.policy_decision === "REQUIRE_APPROVAL";

  if (!pending && !grant) return null;

  return (
    <section className="panel">
      <div className="panel-title">Approval</div>
      <div style={{ padding: "12px 16px 16px" }}>
        {pending && !grant && (
          <>
            <div style={{ marginBottom: 10 }}>
              System C classified this as{" "}
              <span className="pill hold">{governed.risk_class}</span> and stopped
              before writing. An independent re-read of the ERP confirms{" "}
              <strong style={{ color: "var(--allow)" }}>
                {governed.erp.summary}
              </strong>
              .
            </div>
            <button className="approve" onClick={onApprove} disabled={busy}>
              Approve as Demo Administrator
            </button>
          </>
        )}

        {grant && (
          <>
            <table style={{ marginBottom: 12 }}>
              <tbody>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Approved by</td>
                  <td className="mono">{grant.actor}</td>
                </tr>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Scope</td>
                  <td className="mono">{grant.scope}</td>
                </tr>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Granted</td>
                  <td className="mono">{grant.granted_at}</td>
                </tr>
                <tr>
                  <td style={{ color: "var(--muted)" }}>Expires</td>
                  <td className="mono">{grant.expires_at}</td>
                </tr>
              </tbody>
            </table>
            {pending ? (
              <button className="primary" onClick={onRerun} disabled={busy}>
                Re-run the same request
              </button>
            ) : (
              <div>
                Re-run decision:{" "}
                <span className="pill allow">{governed.policy_decision}</span>{" "}
                {governed.postcondition_verified && (
                  <span className="pill allow">postcondition verified</span>
                )}
                <div className="verified">{governed.erp.summary}</div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

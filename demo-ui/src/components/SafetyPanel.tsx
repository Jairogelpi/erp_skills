import type { Evidence } from "../types/demo";
import { formatEstimate } from "./EvidencePanel";

/**
 * Shown immediately after the security scene, and deliberately not
 * flattering.
 *
 * One blocked demo case proves nothing about safety, so the panel leads
 * with the confirmatory H4 result — which was **not supported** — and
 * only then shows the confinement stress test, with the distinction
 * between the two spelled out. Detection and confinement are different
 * properties and the demo must not let one stand in for the other.
 */
export function SafetyPanel({ evidence }: { evidence: Evidence }) {
  const h4 = evidence.cards.find((c) => c.key === "h4_unauthorized_mutation");
  const confinement = evidence.confinement;

  return (
    <section className="panel">
      <div className="panel-title">Safety — what one demo case does not prove</div>

      <div className="warn-banner">
        <strong>ONE DEMO CASE ≠ SECURITY PROOF.</strong> A single blocked request
        is an illustration of the mechanism, not evidence about danger detection.
      </div>

      <div className="split" style={{ padding: "0 16px 16px" }}>
        <div>
          <h4 style={{ margin: "0 0 8px", fontSize: 12.5, color: "var(--muted)" }}>
            Confirmatory H4 — active danger detection
          </h4>
          {h4 ? (
            <table>
              <tbody>
                <tr>
                  <td>Dangerous scenarios</td>
                  <td className="mono">{h4.n?.toLocaleString()}</td>
                </tr>
                <tr>
                  <td>Unauthorized mutation</td>
                  <td className="mono no">{formatEstimate(h4)}</td>
                </tr>
                <tr>
                  <td>Preregistered criterion</td>
                  <td className="mono">{h4.criterion}</td>
                </tr>
                <tr>
                  <td>Result</td>
                  <td className="mono no">NOT SUPPORTED</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="error">H4 unavailable.</div>
          )}
        </div>

        <div>
          <h4 style={{ margin: "0 0 8px", fontSize: 12.5, color: "var(--muted)" }}>
            Confinement stress test — a different question
          </h4>
          {confinement.total_attempts ? (
            <table>
              <tbody>
                <tr>
                  <td>External payloads</td>
                  <td className="mono">{confinement.payloads}</td>
                </tr>
                <tr>
                  <td>Attack surfaces</td>
                  <td className="mono">
                    {Object.keys(confinement.arms ?? {}).length}
                  </td>
                </tr>
                <tr>
                  <td>Total attempts</td>
                  <td className="mono">
                    {confinement.total_attempts.toLocaleString()}
                  </td>
                </tr>
                <tr>
                  <td>Mutations outside contract</td>
                  <td className="mono ok">{confinement.unauthorized_mutations}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <div className="error">Stress-test artifact unavailable.</div>
          )}
        </div>
      </div>

      <div className="note">
        <strong>Detection ≠ confinement.</strong> Danger recognition:{" "}
        <span className="no">insufficient</span> — the governed system failed its
        own preregistered target. Contract escape: not observed in this stress
        test. Neither result licenses the word “secure”.
      </div>
    </section>
  );
}

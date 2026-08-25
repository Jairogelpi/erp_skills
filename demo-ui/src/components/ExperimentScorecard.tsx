import type { Evidence, ParaphraseResult } from "../types/demo";

/**
 * The capability matrix, not a score.
 *
 * Collapsing eight hypotheses with different units, populations and
 * directions into "A = 42 / C = 91" would invent a quantity nothing
 * measured — §36's construct-validity warning applied directly. Each
 * row instead names the hypothesis it derives from so a reader can go
 * check it.
 */
export function CapabilityMatrix({ evidence }: { evidence: Evidence }) {
  return (
    <section className="panel">
      <div className="panel-title">Capability matrix — no overall score, on purpose</div>
      <div style={{ padding: "10px 16px 4px" }}>
        <table>
          <thead>
            <tr>
              <th>Dimension</th>
              <th>A</th>
              <th>B</th>
              <th>C</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {evidence.capability_matrix.map((row) => {
              const positive = row.system_c === "supported";
              return (
                <tr key={row.dimension}>
                  <td>{row.dimension}</td>
                  <td style={{ color: "var(--muted)" }}>{row.system_a}</td>
                  <td style={{ color: "var(--muted)" }}>{row.system_b}</td>
                  <td className={positive ? "ok" : "no"}>{row.system_c}</td>
                  <td className="mono" style={{ color: "var(--dim)" }}>
                    {row.source_hypothesis}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="note">
        Every verdict in the C column is the frozen report’s own, read from{" "}
        {evidence.protocol_tag}. Nothing here is scored or weighted by this UI.
      </div>
    </section>
  );
}

/**
 * Paraphrase consistency for this run, kept visibly separate from H3a.
 * Three phrasings on a laptop are an illustration; the hypothesis was
 * tested on 1,192 scenarios.
 */
export function ParaphrasePanel({
  result,
  evidence,
}: {
  result: ParaphraseResult;
  evidence: Evidence | null;
}) {
  const h3a = evidence?.cards.find((c) => c.key === "h3a") ?? null;

  return (
    <section className="panel">
      <div className="panel-title">Paraphrase stability — this demo run</div>
      <div style={{ padding: "10px 16px 4px" }}>
        <div style={{ marginBottom: 10 }}>
          {result.variants.map((variant, index) => (
            <div key={variant} className="verified" style={{ fontStyle: "normal" }}>
              S{index + 1} · {variant}
            </div>
          ))}
        </div>
        <table>
          <thead>
            <tr>
              <th>System</th>
              {result.variants.map((_, index) => (
                <th key={index} className="mono">
                  S{index + 1}
                </th>
              ))}
              <th>Same outcome</th>
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row) => (
              <tr key={row.system}>
                <td className="mono">{row.system}</td>
                {row.outcomes.map((outcome, index) => (
                  <td key={index} className="mono" style={{ fontSize: 11.5 }}>
                    {outcome}
                  </td>
                ))}
                <td className={row.consistent ? "ok" : "no"}>
                  {row.consistent ? "yes" : "no"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="note">
        {result.disclaimer}
        {h3a && (
          <>
            {" "}
            <strong>Confirmatory H3a</strong> — odds ratio{" "}
            {h3a.effect_size?.toFixed(2)}, p = {h3a.p_value?.toExponential(1)}, n ={" "}
            {h3a.n?.toLocaleString()}.{" "}
            {h3a.supported ? "Supported." : "Not supported."}
          </>
        )}
      </div>
    </section>
  );
}

import type { DemoSystemResult, SystemName } from "../types/demo";

function summarise(
  records: Record<string, Record<string, Record<string, unknown>>>,
): string[] {
  const lines: string[] = [];
  for (const [model, rows] of Object.entries(records)) {
    for (const [id, row] of Object.entries(rows)) {
      const fields = Object.entries(row)
        .filter(([k]) => k !== "id")
        .map(([k, v]) => `${k}=${String(v)}`)
        .join("  ");
      lines.push(`${model} #${id}  ${fields}`);
    }
  }
  return lines.length ? lines : ["(empty)"];
}

/**
 * Before / after / delta for each architecture.
 *
 * The delta is computed by the API from two independent reads of the
 * store, never from what a system reported doing — the same rule §25
 * imposes on postconditions. That is what the caption claims and it has
 * to stay true.
 */
export function ErpStatePanel({
  systems,
}: {
  systems: Record<SystemName, DemoSystemResult>;
}) {
  return (
    <section className="panel">
      <div className="panel-title">Actual ERP state</div>
      <div className="erp">
        {(["A", "B", "C"] as SystemName[]).map((name) => {
          const result = systems[name];
          return (
            <div className="erp-col" key={name}>
              <h4>
                System {name} — {result.label}
              </h4>
              <div className="erp-box">
                <div style={{ color: "var(--muted)", marginBottom: 4 }}>BEFORE</div>
                {summarise(result.erp.before).map((l) => (
                  <div key={l}>{l}</div>
                ))}
                <div style={{ color: "var(--muted)", margin: "9px 0 4px" }}>AFTER</div>
                {summarise(result.erp.after).map((l) => (
                  <div key={l}>{l}</div>
                ))}
              </div>
              <div
                className={`erp-delta ${result.erp.changed ? "changed" : "same"}`}
                style={{ marginTop: 9 }}
              >
                {result.erp.summary}
              </div>
            </div>
          );
        })}
      </div>
      <div className="verified" style={{ padding: "0 16px 14px" }}>
        Verified by independent ERP re-read — the delta compares two reads of the
        store, not what the agent reported doing.
      </div>
    </section>
  );
}

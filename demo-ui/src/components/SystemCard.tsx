import type { DemoSystemResult } from "../types/demo";

const TITLES: Record<string, { name: string; sub: string }> = {
  A: { name: "SYSTEM A", sub: "Direct agent — generic tools" },
  B: { name: "SYSTEM B", sub: "Typed tools — schema validated" },
  C: { name: "ERP AGENT OS — C", sub: "Governed skills" },
};

function decisionClass(decision: string | null): string {
  if (decision === "ALLOW") return "allow";
  if (decision === "DENY") return "deny";
  if (decision === null) return "none";
  // ABSTAIN / CLARIFY / REQUIRE_APPROVAL all mean "held for a human".
  return "hold";
}

function Row({
  label,
  value,
  absent,
}: {
  label: string;
  value: React.ReactNode;
  absent?: boolean;
}) {
  return (
    <div className={absent ? "row absent" : "row"}>
      <span className="k">{label}</span>
      <span className="v">{absent ? "—" : value}</span>
    </div>
  );
}

/**
 * Renders the same field list for every architecture. A and B genuinely
 * have no risk class, policy decision, approval record or postcondition
 * result (CLAUDE.md §18 defines them by that absence), so those rows
 * render as "—" instead of disappearing: the empty rows are the
 * comparison, and hiding them would flatter the ungoverned baselines.
 */
export function SystemCard({ result }: { result: DemoSystemResult }) {
  const meta = TITLES[result.system];
  const absent = new Set(result.unavailable);
  const governed = result.system === "C";

  return (
    <section className={governed ? "panel syscard governed" : "panel syscard"}>
      <header>
        <h3>{meta.name}</h3>
        <div className="sub">{meta.sub}</div>
      </header>

      <div className="rows">
        <Row
          label="Selected capability"
          value={<span>{result.selected_capability ?? "none"}</span>}
        />
        {governed && (
          <Row
            label="Retrieval confidence"
            value={
              result.retrieval_confidence === null
                ? "—"
                : result.retrieval_confidence.toFixed(3)
            }
          />
        )}
        <Row
          label="Arguments"
          value={Object.entries(result.arguments)
            .map(([k, v]) => `${k}=${String(v)}`)
            .join(", ")}
        />
        <Row
          label="Skill version"
          value={result.skill_version ?? "—"}
          absent={absent.has("skill_version")}
        />
        <Row
          label="Risk classification"
          value={result.risk_class}
          absent={absent.has("risk_class")}
        />
        <Row
          label="Policy decision"
          value={
            <span className={`pill ${decisionClass(result.policy_decision)}`}>
              {result.policy_decision}
            </span>
          }
          absent={absent.has("policy_decision")}
        />
        <Row
          label="Approval"
          value={
            result.approval_required
              ? "required"
              : (result.approval_status ?? "not required")
          }
          absent={absent.has("approval_status")}
        />
        <Row label="Handler" value={result.handler ?? "—"} absent={!result.handler} />
        <Row
          label="Execution"
          value={
            <span
              className={`pill ${result.execution_status === "executed" ? "allow" : "none"}`}
            >
              {result.execution_status}
            </span>
          }
        />
        <Row
          label="Postcondition"
          value={
            result.postcondition_verified === null ? (
              "—"
            ) : (
              <span className={`pill ${result.postcondition_verified ? "allow" : "deny"}`}>
                {result.postcondition_verified ? "verified" : "failed"}
              </span>
            )
          }
          absent={absent.has("postcondition_verified")}
        />
        <Row label="Audit id" value={result.audit_id ?? "—"} absent={absent.has("audit_id")} />
        <Row
          label="Tokens"
          value={
            result.tokens === null
              ? "—"
              : result.tokens === 0 && governed
                ? "0 — no LLM call"
                : String(result.tokens)
          }
        />
        {result.error && <Row label="Error" value={result.error} />}
      </div>

      {result.findings.length > 0 && (
        <div className="findings">
          {result.findings.map((f) => (
            <div className="f" key={f}>
              {f}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

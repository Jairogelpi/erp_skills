import { useState } from "react";
import { api } from "../api/client";
import { ContractForm } from "./ContractForm";
import type { DiffEntry, ProposalDescription } from "../types/demo";

type Mode = "create" | "modify";
type View = "form" | "json";

/** Skill Studio (SPEC v2 §9): natural language -> proposal -> diff ->
 * validation -> human approval -> new version. The LLM never activates
 * anything; `/product/skill-studio/approve` requires a named human actor. */
export function SkillStudio() {
  const [mode, setMode] = useState<Mode>("create");
  const [description, setDescription] = useState(
    "Quiero poder marcar como prioridad alta todas las oportunidades " +
      "abiertas de un cliente, pero si afecta a mas de diez oportunidades " +
      "debe pedir aprobacion.",
  );
  const [instruction, setInstruction] = useState(
    "Permite tambien al director comercial usarla y que la aprobacion " +
      "sea obligatoria si afecta a mas de cinco oportunidades.",
  );
  const [contractText, setContractText] = useState("");
  const [view, setView] = useState<View>("form");
  const [diff, setDiff] = useState<DiffEntry[] | null>(null);
  const [tested, setTested] = useState<ProposalDescription | null>(null);
  const [approver, setApprover] = useState("Demo Administrator");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Side-effect-free: safe to call during render (the form view needs
  // the parsed object on every render). Callers that need to report a
  // parse failure to the user call `contract()` instead.
  const parseContract = (): Record<string, unknown> | null => {
    try {
      return JSON.parse(contractText);
    } catch {
      return null;
    }
  };

  const contract = (): Record<string, unknown> | null => {
    const parsed = parseContract();
    if (parsed === null) setError("draft contract is not valid JSON");
    return parsed;
  };

  const doDraft = async () => {
    setBusy(true);
    setError(null);
    setDiff(null);
    setTested(null);
    try {
      const result = await api.draftSkill(description);
      setContractText(JSON.stringify(result.contract, null, 2));
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doModify = async () => {
    const base = contract();
    if (!base) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.modifySkill(base, instruction);
      setContractText(JSON.stringify(result.contract, null, 2));
      setDiff(result.diff);
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doTest = async () => {
    const c = contract();
    if (!c) return;
    setBusy(true);
    setError(null);
    try {
      setTested(await api.testProposal(c));
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doApprove = async () => {
    if (!tested) return;
    setBusy(true);
    setError(null);
    try {
      setTested(await api.approveProposal(tested.skill_id, tested.version, approver));
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="split">
      <section className="panel">
        <div
          className="panel-title"
          style={{ display: "flex", alignItems: "center", gap: 8 }}
        >
          Skill Studio
          {/* CLAUDE.md §21: every Skill Studio screen must carry this,
              always visible -- kept as a small persistent tag rather
              than the earlier full-width banner, so it stays on screen
              without dominating the shot when recording. */}
          <span className="pill hold" title="AI MAY PROPOSE · AI MAY NOT ACTIVATE">
            POST-CORE DEMO
          </span>
        </div>

        <div className="composer">
          <div className="presets" style={{ marginBottom: 10 }}>
            <button
              className={`preset ${mode === "create" ? "active" : ""}`}
              onClick={() => setMode("create")}
            >
              CREATE FROM NATURAL LANGUAGE
            </button>
            <button
              className={`preset ${mode === "modify" ? "active" : ""}`}
              onClick={() => setMode("modify")}
            >
              MODIFY EXISTING SKILL
            </button>
          </div>

          {mode === "create" && (
            <>
              <label>Describe the capability</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <div className="composer-row">
                <button className="primary" onClick={doDraft} disabled={busy}>
                  Generate skill proposal
                </button>
              </div>
            </>
          )}

          {mode === "modify" && (
            <>
              <label>Instruction (applied to the draft above)</label>
              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
              />
              <div className="composer-row">
                <button className="primary" onClick={doModify} disabled={busy}>
                  Apply to draft
                </button>
              </div>
            </>
          )}

          {error && <div className="error">{error}</div>}

          <div
            className="composer-row"
            style={{ marginTop: 14, justifyContent: "space-between" }}
          >
            <label style={{ margin: 0 }}>Draft contract</label>
            <div className="presets">
              <button
                className={`preset ${view === "form" ? "active" : ""}`}
                onClick={() => setView("form")}
                disabled={!contractText}
              >
                Formulario
              </button>
              <button
                className={`preset ${view === "json" ? "active" : ""}`}
                onClick={() => setView("json")}
              >
                JSON
              </button>
            </div>
          </div>

          {view === "form" && contractText && parseContract() && (
            <ContractForm
              contract={parseContract() as Record<string, unknown>}
              onChange={(next) => setContractText(JSON.stringify(next, null, 2))}
            />
          )}
          {view === "form" && contractText && !parseContract() && (
            <div className="error">
              El JSON del contrato no es válido — cambia a la vista JSON
              para corregirlo.
            </div>
          )}
          {view === "form" && !contractText && (
            <div className="note">
              Genera una propuesta primero, o cambia a JSON para pegar un
              contrato.
            </div>
          )}

          {view === "json" && (
            <textarea
              className="mono"
              style={{ minHeight: 260, fontFamily: "var(--mono)" }}
              value={contractText}
              onChange={(e) => setContractText(e.target.value)}
              placeholder="Generate a proposal first, or paste a contract JSON."
            />
          )}

          <div className="composer-row">
            <button onClick={doTest} disabled={busy || !contractText}>
              Validate + sandbox test
            </button>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">Diff CURRENT → PROPOSED</div>
        {!diff && <div className="note">Apply a modification to see a diff.</div>}
        {diff && diff.length === 0 && (
          <div className="note">No field-level change detected.</div>
        )}
        {diff && diff.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Field</th>
                <th>Before</th>
                <th>After</th>
              </tr>
            </thead>
            <tbody>
              {diff.map((d, i) => (
                <tr key={i}>
                  <td className="mono">{d.field}</td>
                  <td className="mono">{JSON.stringify(d.before)}</td>
                  <td className="mono">{JSON.stringify(d.after)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="panel-title" style={{ paddingTop: 16 }}>
          Validation / Sandbox
        </div>
        {!tested && <div className="note">Not yet validated.</div>}
        {tested && (
          <div style={{ padding: "6px 16px 16px" }}>
            <div className="row">
              <span className="k">✓ schema valid</span>
              <span className="v ok">PASS</span>
            </div>
            <div className="row">
              <span className="k">✓ sandbox tests passed</span>
              <span className="v ok">PASS</span>
            </div>
            <div className="row">
              <span className="k">State</span>
              <span className="v">
                DRAFT → VALIDATED → TESTED
                {tested.state === "ACTIVE" ? " → APPROVED → ACTIVE" : ""}
              </span>
            </div>
            <div className="row">
              <span className="k">Skill</span>
              <span className="v">
                {tested.skill_id} · v{tested.version}
              </span>
            </div>

            {tested.sandbox_preview && (
              <>
                <div className="panel-title" style={{ padding: "10px 0 4px" }}>
                  Lo que hizo de verdad en el sandbox
                </div>
                <div className="note" style={{ padding: "0 0 6px" }}>
                  No es una simulación: se ejecutó el handler de esta skill
                  contra un almacén desechable y esto es lo que creó.
                </div>
                <pre
                  className="mono"
                  style={{
                    background: "var(--bg)",
                    border: "1px solid var(--line)",
                    borderRadius: 6,
                    padding: 10,
                    fontSize: 12,
                    overflowX: "auto",
                  }}
                >
                  {JSON.stringify(tested.sandbox_preview.created_record, null, 2)}
                </pre>
              </>
            )}

            {tested.state !== "ACTIVE" && (
              <div className="composer-row">
                <input
                  value={approver}
                  onChange={(e) => setApprover(e.target.value)}
                  placeholder="Named human approver"
                  style={{
                    flex: 1,
                    background: "var(--bg)",
                    color: "var(--text)",
                    border: "1px solid var(--line)",
                    borderRadius: 6,
                    padding: "8px 10px",
                  }}
                />
                <button className="approve" onClick={doApprove} disabled={busy}>
                  Approve skill
                </button>
              </div>
            )}
            {tested.state === "ACTIVE" && (
              <div className="row">
                <span className="k">Activated</span>
                <span className="v ok">
                  ACTIVE v{tested.version} — a human approved this
                </span>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

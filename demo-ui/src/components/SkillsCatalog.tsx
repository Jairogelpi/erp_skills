import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SkillDetailView, SkillView } from "../types/demo";

/** Skills Catalog + Skill Detail (SPEC v2 §7/§8): the frozen 12-skill
 * catalog, read from the seeded registry so state/version/history are
 * real, not the bare static list. */
const TERMINAL_STATES = new Set(["DEPRECATED", "QUARANTINED"]);

export function SkillsCatalog() {
  const [skills, setSkills] = useState<SkillView[]>([]);
  const [detail, setDetail] = useState<SkillDetailView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actor, setActor] = useState("Demo Administrator");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const refreshList = () =>
    api.skills().then(setSkills).catch((exc: Error) => setError(exc.message));

  useEffect(() => {
    refreshList();
  }, []);

  const open = async (skillId: string) => {
    try {
      setDetail(await api.skillDetail(skillId));
    } catch (exc) {
      setError((exc as Error).message);
    }
  };

  const doQuarantine = async () => {
    if (!detail || !actor.trim() || !reason.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setDetail(await api.quarantineSkill(detail.skill_id, actor, reason));
      setReason("");
      await refreshList();
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doDeprecate = async () => {
    if (!detail || !actor.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setDetail(await api.deprecateSkill(detail.skill_id, actor));
      await refreshList();
    } catch (exc) {
      setError((exc as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="split">
      <section className="panel">
        <div className="panel-title">Skills Catalog — {skills.length} skills</div>
        {error && <div className="error">{error}</div>}
        <div className="cards">
          {skills.map((s) => (
            <button
              key={s.skill_id}
              className="evcard"
              style={{ textAlign: "left", cursor: "pointer" }}
              onClick={() => open(s.skill_id)}
            >
              <div className="t">{s.description}</div>
              <div className="figure" style={{ fontSize: 14 }}>
                {s.skill_id}
              </div>
              <div className="row">
                <span className="k">Version</span>
                <span className="v">
                  {s.state} · v{s.version} · {s.risk_class}
                </span>
              </div>
              <div className="row">
                <span className="k">Roles</span>
                <span className="v">{s.allowed_roles.join(", ")}</span>
              </div>
              {s.odoo_wired && (
                <span className="pill allow" style={{ marginTop: 6 }}>
                  ODOO WIRED
                </span>
              )}
            </button>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">Skill Detail</div>
        {!detail && <div className="note">Select a skill from the catalog.</div>}
        {detail && (
          <div style={{ padding: "10px 16px 16px" }}>
            <div className="row">
              <span className="k">Identity</span>
              <span className="v">{detail.skill_id}</span>
            </div>
            <div className="row">
              <span className="k">Lifecycle</span>
              <span className="v">DRAFT → VALIDATED → APPROVED → ACTIVE</span>
            </div>
            <div className="row">
              <span className="k">Current state</span>
              <span className="v">
                {detail.state} · v{detail.version}
              </span>
            </div>
            <div className="row">
              <span className="k">Versions</span>
              <span className="v">{detail.versions.join(", ")}</span>
            </div>
            <div className="row">
              <span className="k">Risk / Policy</span>
              <span className="v">{detail.risk_class}</span>
            </div>
            <div className="row">
              <span className="k">Roles</span>
              <span className="v">{detail.allowed_roles.join(", ")}</span>
            </div>
            <div className="row">
              <span className="k">Handler</span>
              <span className="v">{detail.handler}</span>
            </div>
            <div className="row">
              <span className="k">Idempotency</span>
              <span className="v">{detail.idempotent ? "idempotent" : "no"}</span>
            </div>
            <div className="row">
              <span className="k">Preconditions</span>
              <span className="v">{detail.preconditions.join(", ") || "—"}</span>
            </div>
            <div className="row">
              <span className="k">Postconditions</span>
              <span className="v">{detail.postconditions.join(", ")}</span>
            </div>

            <div className="panel-title" style={{ padding: "12px 0 6px" }}>
              Lifecycle
            </div>
            {TERMINAL_STATES.has(detail.state) ? (
              <div className="note" style={{ padding: "0 0 8px" }}>
                {detail.state === "QUARANTINED"
                  ? "Suspendida. No hay reactivación en este ciclo de vida — es el freno de emergencia, terminal a propósito."
                  : "Retirada. No hay vuelta a ACTIVE en este ciclo de vida — es la retirada planificada, terminal a propósito."}
              </div>
            ) : (
              <>
                <div className="note" style={{ padding: "0 0 8px" }}>
                  No hay "borrar": ningún módulo de este sistema tiene
                  eliminación física. Solo suspender (inmediato, desde
                  cualquier estado) o retirar (planificado, solo desde
                  ACTIVE) — ninguno reversible.
                </div>
                <div className="composer-row">
                  <input
                    value={actor}
                    onChange={(e) => setActor(e.target.value)}
                    placeholder="Tu nombre"
                    style={{
                      flex: 1,
                      background: "var(--bg)",
                      color: "var(--text)",
                      border: "1px solid var(--line)",
                      borderRadius: 8,
                      padding: "7px 10px",
                      fontSize: 12.5,
                    }}
                  />
                  <input
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Motivo de la suspensión"
                    style={{
                      flex: 2,
                      background: "var(--bg)",
                      color: "var(--text)",
                      border: "1px solid var(--line)",
                      borderRadius: 8,
                      padding: "7px 10px",
                      fontSize: 12.5,
                    }}
                  />
                </div>
                <div className="composer-row">
                  <button
                    className="approve"
                    onClick={doQuarantine}
                    disabled={busy || !actor.trim() || !reason.trim()}
                  >
                    Suspender
                  </button>
                  <button
                    onClick={doDeprecate}
                    disabled={busy || !actor.trim()}
                  >
                    Retirar
                  </button>
                </div>
              </>
            )}

            <div className="panel-title" style={{ padding: "12px 0 6px" }}>
              Audit history
            </div>
            <table>
              <thead>
                <tr>
                  <th>From</th>
                  <th>To</th>
                  <th>Actor</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {detail.history.map((h, i) => (
                  <tr key={i}>
                    <td className="mono">{h.from || "—"}</td>
                    <td className="mono">{h.to}</td>
                    <td>{h.actor}</td>
                    <td>{h.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

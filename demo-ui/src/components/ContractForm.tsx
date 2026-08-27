import { useState } from "react";
import { api } from "../api/client";
import type { ApprovalEvaluation } from "../types/demo";

/** Business-readable editor for a skill contract, over the same JSON the
 * backend actually validates. Most people reading this demo don't know
 * what JSON is — this renders the handful of fields a business owner
 * would actually want to change (name, risk, who can use it, what
 * information it needs, when it needs approval) as labelled controls.
 * Nothing here reinterprets the contract: every change writes straight
 * back into the same object `contractText` already holds, so
 * Validate/Approve/Modify keep working exactly as before.
 *
 * Fields left out on purpose: `postconditions` and `execution.handler`.
 * Both are safety-relevant and neither is something a business user
 * should freely rewrite in this demo -- they stay visible read-only, and
 * still editable via the raw JSON view for a technical reviewer. */

type ParamRow = { name: string; type: "string" | "number" | "boolean" };

const RISK_LABELS: Record<string, string> = {
  R0: "R0 — Consulta (solo lectura)",
  R1: "R1 — Escritura de bajo impacto",
  R2: "R2 — Modificación relevante",
  R3: "R3 — Alto impacto",
};

function inputSchemaToRows(schema: unknown): ParamRow[] {
  if (typeof schema !== "object" || schema === null) return [];
  const s = schema as { properties?: Record<string, { type?: string }> };
  const properties = s.properties ?? {};
  return Object.entries(properties).map(([name, def]) => ({
    name,
    type: (def?.type as ParamRow["type"]) ?? "string",
  }));
}

function rowsToInputSchema(rows: ParamRow[]): Record<string, unknown> {
  const properties: Record<string, { type: string }> = {};
  for (const row of rows) {
    if (row.name.trim()) properties[row.name.trim()] = { type: row.type };
  }
  return {
    type: "object",
    required: rows.map((r) => r.name.trim()).filter(Boolean),
    properties,
  };
}

/** Label above control, full width -- the `.row` key/value pair layout
 * elsewhere in this app is for short one-line facts and squashes a
 * long label and a wide input into two cramped columns. A form field
 * needs the composer's stacked layout instead. `caption` is optional
 * small helper text under the label, for a rule that needs one more
 * sentence than the label can carry on its own. */
function field(label: string, value: React.ReactNode, caption?: string) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label
        style={{
          display: "block",
          fontSize: 12.5,
          color: "var(--muted)",
          marginBottom: 5,
        }}
      >
        {label}
      </label>
      {value}
      {caption && (
        <div style={{ fontSize: 11, color: "var(--dim)", marginTop: 4 }}>{caption}</div>
      )}
    </div>
  );
}

const textInputStyle: React.CSSProperties = {
  display: "block",
  boxSizing: "border-box",
  width: "100%",
  background: "var(--bg)",
  color: "var(--text)",
  border: "1px solid var(--line)",
  borderRadius: 6,
  padding: "7px 9px",
  fontFamily: "var(--sans)",
  fontSize: 12.5,
};

export function ContractForm({
  contract,
  onChange,
}: {
  contract: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}) {
  const permissions = (contract.permissions as { allowed_roles?: string[] }) ?? {};
  const approvalRules = (contract.approval_required_when as string[] | undefined) ?? [];
  const paramRows = inputSchemaToRows(contract.input_schema);

  const set = (patch: Record<string, unknown>) => onChange({ ...contract, ...patch });

  const setRow = (index: number, patch: Partial<ParamRow>) => {
    const rows = paramRows.map((r, i) => (i === index ? { ...r, ...patch } : r));
    set({ input_schema: rowsToInputSchema(rows) });
  };
  const addRow = () =>
    set({ input_schema: rowsToInputSchema([...paramRows, { name: "", type: "string" }]) });
  const removeRow = (index: number) =>
    set({ input_schema: rowsToInputSchema(paramRows.filter((_, i) => i !== index)) });

  return (
    <div style={{ paddingTop: 6 }}>
      {field(
        "Nombre / descripción",
        <textarea
          style={textInputStyle}
          rows={2}
          value={(contract.description as string) ?? ""}
          onChange={(e) => set({ description: e.target.value })}
        />,
      )}

      {field(
        "Nivel de riesgo",
        <select
          style={textInputStyle}
          value={(contract.risk_class as string) ?? "R1"}
          onChange={(e) => set({ risk_class: e.target.value })}
        >
          {Object.entries(RISK_LABELS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>,
      )}

      {field(
        "Quién puede usarla",
        <RoleChips
          roles={permissions.allowed_roles ?? []}
          onChange={(roles) => set({ permissions: { allowed_roles: roles } })}
        />,
      )}

      {field(
        "Cuándo necesita aprobación humana",
        <textarea
          style={textInputStyle}
          rows={2}
          placeholder="Escribe en tus propias palabras, ej: si afecta a más de 10 oportunidades"
          value={approvalRules.join("\n")}
          onChange={(e) =>
            set({
              approval_required_when: e.target.value
                .split("\n")
                .map((r) => r.trim())
                .filter(Boolean),
            })
          }
        />,
        "Una condición por línea, en lenguaje normal. Puedes probarla abajo. " +
          "Nota: fuera de esta pantalla, lo que de verdad exige aprobación " +
          "para ejecutar es el nivel de riesgo elegido arriba (R2 y R3 " +
          "siempre la piden) — esta condición es una capa adicional, " +
          "propia de esta demo de producto.",
      )}

      <ApprovalTester conditions={approvalRules} />

      <div className="panel-title" style={{ padding: "10px 0 4px" }}>
        Datos que necesita (parámetros)
      </div>
      {paramRows.length === 0 && (
        <div className="note" style={{ padding: "2px 0 8px" }}>
          Sin parámetros. Añade uno abajo.
        </div>
      )}
      {paramRows.map((row, i) => (
        <div
          key={i}
          className="composer-row"
          style={{ marginTop: 6, alignItems: "center" }}
        >
          <input
            style={{ ...textInputStyle, flex: 2 }}
            placeholder="nombre del dato"
            value={row.name}
            onChange={(e) => setRow(i, { name: e.target.value })}
          />
          <select
            style={{ ...textInputStyle, flex: 1 }}
            value={row.type}
            onChange={(e) => setRow(i, { type: e.target.value as ParamRow["type"] })}
          >
            <option value="string">texto</option>
            <option value="number">número</option>
            <option value="boolean">sí/no</option>
          </select>
          <button onClick={() => removeRow(i)} title="Quitar">
            ✕
          </button>
        </div>
      ))}
      <div className="composer-row" style={{ marginTop: 8 }}>
        <button onClick={addRow}>+ Añadir dato</button>
      </div>

      <div className="panel-title" style={{ padding: "14px 0 4px" }}>
        No editable aquí (seguridad)
      </div>
      {field(
        "Se comprueba después de ejecutar",
        <span className="mono">
          {((contract.postconditions as string[] | undefined) ?? []).join(", ") || "—"}
        </span>,
      )}
      {field(
        "Handler",
        <span className="mono">
          {String(
            (contract.execution as { handler?: string } | undefined)?.handler ?? "",
          )}
        </span>,
      )}
    </div>
  );
}

/** "Who can use this" as removable chips instead of comma-separated
 * text -- a non-technical viewer reads "escribe un rol y pulsa Enter",
 * not a syntax rule about commas. */
function RoleChips({
  roles,
  onChange,
}: {
  roles: string[];
  onChange: (roles: string[]) => void;
}) {
  const [draft, setDraft] = useState("");

  const commit = () => {
    const value = draft.trim();
    if (value && !roles.includes(value)) onChange([...roles, value]);
    setDraft("");
  };

  return (
    <div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 6 }}>
        {roles.map((role) => (
          <span key={role} className="pill none" style={{ display: "flex", gap: 6 }}>
            {role}
            <button
              onClick={() => onChange(roles.filter((r) => r !== role))}
              title={`Quitar ${role}`}
              style={{ padding: 0, border: "none", background: "none", cursor: "pointer" }}
            >
              ✕
            </button>
          </span>
        ))}
        {roles.length === 0 && (
          <span className="note" style={{ padding: 0 }}>
            Nadie puede usarla todavía — añade al menos un rol.
          </span>
        )}
      </div>
      <input
        style={textInputStyle}
        value={draft}
        placeholder="escribe un rol y pulsa Enter (ej. director comercial)"
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commit();
          }
        }}
        onBlur={commit}
      />
    </div>
  );
}

/** Live test of the free-text approval conditions against a number the
 * presenter types in -- isolated on purpose (see
 * evaluate_approval_conditions' docstring): this calls one small,
 * self-contained endpoint, never the real execution path, so trying it
 * cannot affect anything else in the project. */
function ApprovalTester({ conditions }: { conditions: string[] }) {
  const [count, setCount] = useState("15");
  const [result, setResult] = useState<ApprovalEvaluation | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    const affectedCount = Number(count);
    if (!Number.isFinite(affectedCount) || affectedCount < 0) return;
    setBusy(true);
    try {
      setResult(await api.evaluateApproval(conditions, affectedCount));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        marginTop: -6,
        marginBottom: 14,
        padding: "10px 12px",
        background: "var(--panel-2)",
        border: "1px solid var(--line)",
        borderRadius: 8,
      }}
    >
      <div style={{ fontSize: 11.5, color: "var(--dim)", marginBottom: 8 }}>
        PROBAR ESTA CONDICIÓN
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span style={{ fontSize: 12.5 }}>Si afectara a</span>
        <input
          type="number"
          min={0}
          style={{ ...textInputStyle, width: 70 }}
          value={count}
          onChange={(e) => setCount(e.target.value)}
        />
        <span style={{ fontSize: 12.5 }}>registros...</span>
        <button onClick={run} disabled={busy || conditions.length === 0}>
          Probar
        </button>
      </div>
      {conditions.length === 0 && (
        <div className="note" style={{ padding: "6px 0 0" }}>
          Escribe una condición arriba primero.
        </div>
      )}
      {result && (
        <div style={{ marginTop: 8, fontSize: 12.5 }}>
          {result.requires_approval ? (
            <span className="pill hold">SÍ, PEDIRÍA APROBACIÓN</span>
          ) : (
            <span className="pill allow">NO, SE EJECUTARÍA SOLA</span>
          )}
          {result.unparsed_conditions.length > 0 && (
            <div style={{ color: "var(--dim)", marginTop: 6 }}>
              No entendí esta condición, la ignoré:{" "}
              {result.unparsed_conditions.join("; ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

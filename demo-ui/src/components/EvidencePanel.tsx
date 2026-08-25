import { useState } from "react";
import type { Evidence, HypothesisCard } from "../types/demo";

/**
 * Formats an estimate for display. The *value* always comes from the
 * API (which reads the frozen report); this only chooses units, and it
 * refuses to invent one when the report has none.
 */
export function formatEstimate(card: HypothesisCard): string {
  if (card.estimate === null) return "n/a";
  switch (card.estimate_kind) {
    case "percentage_points": {
      const pp = card.estimate * 100;
      return `${pp > 0 ? "+" : ""}${pp.toFixed(1)} pp`;
    }
    case "tokens":
      return `${card.estimate > 0 ? "+" : ""}${card.estimate.toFixed(2)}`;
    case "proportion":
      return `${(card.estimate * 100).toFixed(1)} %`;
    default:
      return String(card.estimate);
  }
}

function formatP(p: number | null): string {
  if (p === null) return "not applicable for this test";
  if (p < 0.001) return p.toExponential(2);
  return p.toFixed(3);
}

function Drilldown({ card }: { card: HypothesisCard }) {
  return (
    <div className="drill">
      <dl>
        <dt>Question</dt>
        <dd style={{ fontFamily: "var(--sans)" }}>{card.question}</dd>
        <dt>Population</dt>
        <dd>
          {card.population ?? "—"} — n = {card.n?.toLocaleString() ?? "—"}{" "}
          {card.unit ? `(${card.unit})` : ""}
        </dd>
        <dt>Method</dt>
        <dd>{card.test ?? "—"}</dd>
        <dt>Decision criterion</dt>
        <dd>{card.criterion ?? "—"}</dd>
        <dt>Estimate</dt>
        <dd>{formatEstimate(card)}</dd>
        <dt>95% CI</dt>
        <dd>
          [{card.ci_low === null ? "−∞" : card.ci_low.toFixed(4)},{" "}
          {card.ci_high === null ? "+∞" : card.ci_high.toFixed(4)}]
        </dd>
        <dt>Effect size</dt>
        <dd>
          {card.effect_size === null
            ? "—"
            : `${card.effect_size.toFixed(4)} (${card.effect_size_name ?? "—"})`}
        </dd>
        <dt>p</dt>
        <dd>{formatP(card.p_value)}</dd>
        <dt>Verdict</dt>
        <dd>{card.verdict}</dd>
        <dt>Evidence state</dt>
        <dd>{card.evidence_state}</dd>
      </dl>
    </div>
  );
}

export function EvidencePanel({ evidence }: { evidence: Evidence }) {
  const [open, setOpen] = useState<string | null>(null);
  const selected = evidence.cards.find((c) => c.key === open) ?? null;

  return (
    <section className="panel">
      <div className="panel-title">
        Confirmatory evidence — {evidence.protocol_tag} ·{" "}
        {evidence.observation_count.toLocaleString()} observations ·{" "}
        {evidence.campaign_state}
      </div>

      <div className="cards">
        {evidence.cards.map((card) => (
          <button
            key={card.key}
            className={`evcard ${card.supported ? "supported" : "not-supported"}`}
            onClick={() => setOpen(open === card.key ? null : card.key)}
          >
            <div className="t">{card.title}</div>
            <div className="figure">{formatEstimate(card)}</div>
            <div className="state">
              {card.supported ? "SUPPORTED" : "NOT SUPPORTED"}
            </div>
          </button>
        ))}
      </div>

      {selected && <Drilldown card={selected} />}

      <div className="note">
        Click any figure for its population, method, criterion and interval. A red
        card means a preregistered hypothesis was <strong>not supported</strong> —
        that is a finding, not a defect.
      </div>
    </section>
  );
}

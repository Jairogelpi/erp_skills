import type { Evidence } from "../types/demo";

export function Header({ evidence }: { evidence: Evidence | null }) {
  return (
    <header className="header">
      <div className="brand">
        <h1>ERP AGENT OS</h1>
        <p>Control plane for AI agents operating your ERP — use any agent, control what it can do.</p>
      </div>
      <div className="header-right">
        {evidence ? (
          <>
            <div className="count">
              {evidence.observation_count.toLocaleString()} observations
            </div>
            <div className="tag">
              {evidence.protocol_tag} · {evidence.campaign_state}
            </div>
          </>
        ) : (
          /* Never a placeholder number: an unreadable artifact must read
             as unavailable, not as a plausible statistic. */
          <div className="tag">evidence unavailable</div>
        )}
      </div>
    </header>
  );
}

export function RequestComposer({
  presets,
  activePreset,
  text,
  busy,
  onSelectPreset,
  onChangeText,
  onRun,
}: {
  presets: { id: string; label: string; description: string }[];
  activePreset: string;
  text: string;
  busy: boolean;
  onSelectPreset: (id: string) => void;
  onChangeText: (value: string) => void;
  onRun: () => void;
}) {
  const active = presets.find((p) => p.id === activePreset);
  return (
    <section className="panel composer">
      <label htmlFor="request">What do you want to do in the ERP?</label>
      <textarea
        id="request"
        value={text}
        onChange={(event) => onChangeText(event.target.value)}
        spellCheck={false}
      />
      <div className="composer-row">
        {/* Presets exist so nothing is typed live on camera. */}
        <div className="presets">
          {presets.map((preset) => (
            <button
              key={preset.id}
              className={`preset ${preset.id === activePreset ? "active" : ""}`}
              onClick={() => onSelectPreset(preset.id)}
              disabled={busy}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <button className="primary" onClick={onRun} disabled={busy}>
          {busy ? "Running…" : "Run A / B / C"}
        </button>
        {active && (
          <span style={{ color: "var(--muted)", fontSize: 12 }}>
            {active.description}
          </span>
        )}
      </div>
    </section>
  );
}

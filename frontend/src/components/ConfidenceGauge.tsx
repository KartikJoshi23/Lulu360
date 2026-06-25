export function ConfidenceGauge({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const color =
    value >= 0.7 ? "var(--c-trust)" : value >= 0.5 ? "var(--c-caution)" : "var(--c-alert)";
  return (
    <div style={{ marginTop: 4 }}>
      <div className="kv" style={{ borderBottom: 0, paddingBottom: 4 }}>
        <span className="k">Confidence</span>
        <span className="v">{pct}%</span>
      </div>
      <div className="gauge">
        <span style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

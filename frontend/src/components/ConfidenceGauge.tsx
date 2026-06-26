export function ConfidenceGauge({ value }: { value: number }) {
  const v = Math.max(0, Math.min(1, value));
  const pct = Math.round(v * 100);
  const color =
    v >= 0.7 ? "var(--c-trust)" : v >= 0.5 ? "var(--c-caution)" : "var(--c-alert)";

  const r = 30;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - v);

  return (
    <div className="rgauge">
      <svg className="rgauge-svg" viewBox="0 0 76 76">
        <circle className="rgauge-track" cx="38" cy="38" r={r} />
        <circle
          className="rgauge-fill"
          cx="38"
          cy="38"
          r={r}
          style={{ stroke: color, strokeDasharray: circ, strokeDashoffset: offset }}
        />
      </svg>
      <div className="rgauge-label">
        <b style={{ color }}>{pct}%</b>
        <span>confidence</span>
      </div>
    </div>
  );
}

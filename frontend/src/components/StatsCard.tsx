import { useEffect, useState } from "react";
import { getStats } from "../api/client";
import type { StatsResponse } from "../types";

export function StatsCard({ refreshKey }: { refreshKey: number }) {
  const [s, setS] = useState<StatsResponse | null>(null);

  useEffect(() => {
    let alive = true;
    getStats()
      .then((x) => alive && setS(x))
      .catch(() => alive && setS(null));
    return () => {
      alive = false;
    };
  }, [refreshKey]);

  if (!s || s.total === 0) return null;

  return (
    <div className="stat-grid" style={{ marginTop: 20 }}>
      <div className="glass stat">
        <div className="num" style={{ color: "var(--c-trust)" }}>
          {Math.round(s.automation_rate * 100)}%
        </div>
        <div className="lbl">Automation rate</div>
      </div>
      <div className="glass stat">
        <div className="num">{s.total}</div>
        <div className="lbl">Resolved</div>
      </div>
      <div className="glass stat">
        <div className="num" style={{ color: s.escalated ? "var(--c-alert)" : "var(--ink)" }}>
          {s.escalated}
        </div>
        <div className="lbl">Escalated</div>
      </div>
      <div className="glass stat">
        <div className="num" style={{ color: "var(--c-action)" }}>
          {s.emails_sent}
        </div>
        <div className="lbl">Emails sent</div>
      </div>
    </div>
  );
}

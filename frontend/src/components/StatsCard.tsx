import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { getStats } from "../api/client";
import type { StatsResponse } from "../types";

/** Ease-out count-up to `target`. Animates with rAF when the tab is visible, and
 *  always snaps to the final value via a timeout (so it stays correct even when
 *  rAF is paused in a background tab). */
function useCountUp(target: number, duration = 900) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const step = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      setVal(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    const snap = window.setTimeout(() => setVal(target), duration + 80);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(snap);
    };
  }, [target, duration]);
  return val;
}

function Stat({ value, label, accent, suffix = "" }: {
  value: number; label: string; accent: string; suffix?: string;
}) {
  const n = useCountUp(value);
  return (
    <div className="glass stat" style={{ "--accent": accent } as CSSProperties}>
      <div className="num">{Math.round(n)}{suffix}</div>
      <div className="lbl">{label}</div>
      <span className="spark" />
    </div>
  );
}

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
      <Stat value={Math.round(s.automation_rate * 100)} suffix="%" label="Automation rate" accent="var(--c-trust)" />
      <Stat value={s.total} label="Resolved" accent="var(--c-action)" />
      <Stat value={s.escalated} label="Escalated" accent="var(--c-alert)" />
      <Stat value={s.emails_sent} label="Emails sent" accent="var(--c-voice)" />
    </div>
  );
}

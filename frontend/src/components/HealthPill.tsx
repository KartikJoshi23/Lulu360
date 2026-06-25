import { useEffect, useState } from "react";
import { getHealth, DEMO_MODE } from "../api/client";
import type { HealthResponse } from "../types";

export function HealthPill() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    let alive = true;
    getHealth()
      .then((h) => alive && setHealth(h))
      .catch(() => alive && setDown(true));
    return () => {
      alive = false;
    };
  }, []);

  if (DEMO_MODE) {
    return (
      <span className="pill" title="Serving precomputed responses">
        <span className="dot warn" /> Demo mode
      </span>
    );
  }
  if (down) {
    return (
      <span className="pill" title="Backend unreachable">
        <span className="dot off" /> API offline
      </span>
    );
  }
  if (!health) {
    return (
      <span className="pill">
        <span className="dot" /> Connecting…
      </span>
    );
  }

  const reader = health.reader_backend === "lstm" ? "LSTM live" : "Keyword mode";
  return (
    <span className="pill" title={`FLAN-T5 ${health.flan_enabled ? "enabled" : "template fallback"}`}>
      <span className="dot ok" /> API · {reader}
    </span>
  );
}

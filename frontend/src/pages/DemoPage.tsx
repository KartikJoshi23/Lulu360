import { useState } from "react";
import { ComplaintForm } from "../components/ComplaintForm";
import { ResultsPanel } from "../components/ResultsPanel";
import { StatsCard } from "../components/StatsCard";
import { resolve } from "../api/client";
import type { ResolveResponse } from "../types";

export function DemoPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResolveResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statsKey, setStatsKey] = useState(0);

  async function handleResolve(message: string, customerId: string) {
    setLoading(true);
    setError(null);
    try {
      setResult(await resolve(message, customerId));
      setStatsKey((k) => k + 1); // refresh the automation-rate card
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container page">
      <h1 className="h1">Resolve a complaint</h1>
      <p className="sub">
        Watch a customer message flow through all four AI modules — Reader → Investigator →
        Economist → Voice — and see the fair, auditable resolution.
      </p>

      <ComplaintForm loading={loading} onResolve={handleResolve} />

      <StatsCard refreshKey={statsKey} />

      {error && (
        <div className="glass notice error" style={{ marginTop: 20 }}>
          ⚠️ {error}
        </div>
      )}

      {result && !error && <ResultsPanel result={result} />}

      {!result && !error && (
        <div className="glass notice" style={{ marginTop: 20 }}>
          Enter a complaint or pick a scenario chip above to run the pipeline.
        </div>
      )}
    </div>
  );
}

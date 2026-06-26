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
      setStatsKey((k) => k + 1);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container page">
      <h1 className="h1">Resolve a customer case</h1>
      <p className="sub">
        Watch a Lulu customer message flow through Reader, Investigator, Economist, and Voice
        to produce a fair, auditable response.
      </p>

      <StatsCard refreshKey={statsKey} />

      <ComplaintForm loading={loading} onResolve={handleResolve} />

      {loading && (
        <div className="glass" style={{ marginTop: 20 }}>
          <div className="pipeline-loading">
            {["Reader", "Investigator", "Economist", "Voice"].map((name, i) => (
              <span key={name} style={{ display: "contents" }}>
                {i > 0 && <span className="pl-arrow">-&gt;</span>}
                <span className="pl-step">
                  <span className="pl-dot" style={{ animationDelay: `${i * 0.18}s` }} />
                  <span className="pl-name">{name}</span>
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {!loading && error && (
        <div className="glass notice error" style={{ marginTop: 20 }}>
          {error}
        </div>
      )}

      {!loading && result && !error && <ResultsPanel result={result} />}

      {!loading && !result && !error && (
        <div className="glass notice" style={{ marginTop: 20 }}>
          Enter a complaint, question, or scenario chip above to run the pipeline.
        </div>
      )}
    </div>
  );
}

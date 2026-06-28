import { useState } from "react";
import { runAll } from "../api/client";
import type { RunAllSummary } from "../types";

/** Runs the whole messages.csv dataset through the pipeline in one batch, then
 *  reports back so the KPIs and audit trail can refresh. */
export function RunAllButton({ onDone }: { onDone?: (s: RunAllSummary) => void }) {
  const [running, setRunning] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [err, setErr] = useState(false);

  async function go() {
    setRunning(true);
    setNote(null);
    setErr(false);
    try {
      const s = await runAll();
      setNote(
        `Processed ${s.messages_processed} cases · ${s.emails_sent} emails sent · ` +
          `${Math.round(s.automation_rate * 100)}% automated`,
      );
      onDone?.(s);
    } catch (e) {
      setErr(true);
      setNote(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="runall">
      <button className="runall-btn" onClick={go} disabled={running}>
        {running ? (
          <>
            <span className="spinner" /> Running all cases…
          </>
        ) : (
          <>▶ Run all messages</>
        )}
      </button>
      {running && <span className="runall-hint">Resolving the full dataset — this takes a few seconds.</span>}
      {note && !running && (
        <span className={`runall-note${err ? " err" : ""}`}>{note}</span>
      )}
    </div>
  );
}

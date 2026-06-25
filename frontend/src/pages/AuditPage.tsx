import { useEffect, useState } from "react";
import { getAudit } from "../api/client";
import { StatsCard } from "../components/StatsCard";
import type { AuditRow } from "../types";

function amount(r: AuditRow): string {
  if (r.coupon_percent > 0) return `${r.coupon_percent}% coupon`;
  if (r.wallet_credit > 0) return `AED ${r.wallet_credit}`;
  if (r.action === "REFUND") return "Full refund";
  return "—";
}

function when(ts: string): string {
  const d = new Date(ts);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
}

export function AuditPage() {
  const [rows, setRows] = useState<AuditRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getAudit()
      .then((r) => alive && setRows(r))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load audit log."));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="container page">
      <h1 className="h1">Audit trail</h1>
      <p className="sub">Every money action LuluCare 360 takes is logged here for review.</p>

      <StatsCard refreshKey={0} />

      {error && <div className="glass notice error" style={{ marginTop: 20 }}>⚠️ {error}</div>}

      {rows && rows.length === 0 && (
        <div className="glass notice" style={{ marginTop: 20 }}>
          No money actions logged yet. Resolve a few complaints on the Demo page.
        </div>
      )}

      {rows && rows.length > 0 && (
        <div className="glass" style={{ marginTop: 20, padding: 6, overflowX: "auto" }}>
          <table className="audit">
            <thead>
              <tr>
                <th>Audit ID</th>
                <th>Time</th>
                <th>Customer</th>
                <th>Action</th>
                <th>Logistics</th>
                <th>Amount</th>
                <th>Email subject</th>
              </tr>
            </thead>
            <tbody>
              {[...rows].reverse().map((r, i) => (
                <tr key={`${r.audit_id}-${i}`}>
                  <td>{r.audit_id}</td>
                  <td>{when(r.timestamp)}</td>
                  <td>{r.customer_id}</td>
                  <td>{r.action}</td>
                  <td>{r.refund_type === "NONE" ? "—" : r.refund_type}</td>
                  <td>{amount(r)}</td>
                  <td>{r.email?.subject ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

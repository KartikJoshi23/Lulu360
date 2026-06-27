import { useEffect, useMemo, useState } from "react";
import { getAudit } from "../api/client";
import { StatsCard } from "../components/StatsCard";
import type { AuditRow } from "../types";

function amount(r: AuditRow): string {
  if (r.coupon_percent > 0) return `${r.coupon_percent}% coupon`;
  if (r.wallet_credit > 0) return `AED ${r.wallet_credit}`;
  if (r.action === "REFUND") return "Full refund";
  return "-";
}

function when(ts: string): string {
  const d = new Date(ts);
  return isNaN(d.getTime()) ? ts : d.toLocaleString();
}

type SortKey = "audit_id" | "timestamp" | "customer_id" | "action";

export function AuditPage() {
  const [rows, setRows] = useState<AuditRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "timestamp", dir: -1 });

  useEffect(() => {
    let alive = true;
    getAudit()
      .then((r) => alive && setRows(r))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Failed to load audit log."));
    return () => {
      alive = false;
    };
  }, []);

  const view = useMemo(() => {
    if (!rows) return [];
    const q = filter.trim().toLowerCase();
    const filtered = q
      ? rows.filter(
          (r) =>
            r.customer_id.toLowerCase().includes(q) ||
            r.action.toLowerCase().includes(q) ||
            r.audit_id.toLowerCase().includes(q),
        )
      : rows;
    const sorted = [...filtered].sort((a, b) => {
      const av = String(a[sort.key] ?? "");
      const bv = String(b[sort.key] ?? "");
      return av < bv ? -sort.dir : av > bv ? sort.dir : 0;
    });
    return sorted;
  }, [rows, filter, sort]);

  function toggleSort(key: SortKey) {
    setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: 1 }));
  }

  function arrow(key: SortKey) {
    if (sort.key !== key) return "";
    return sort.dir === 1 ? " ▲" : " ▼";
  }

  return (
    <div className="container page">
      <h1 className="h1">Audit trail</h1>
      <p className="sub">Every money action LuluCare 360 takes is logged here for review.</p>

      <StatsCard refreshKey={0} />

      {error && <div className="glass notice error" style={{ marginTop: 20 }}>{error}</div>}

      {rows && rows.length === 0 && (
        <div className="glass notice" style={{ marginTop: 20 }}>
          No money actions logged yet. Resolve a few complaints on the Demo page.
        </div>
      )}

      {rows && rows.length > 0 && (
        <>
          <div className="audit-toolbar">
            <input
              className="input"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter by customer, action, or audit ID..."
              aria-label="Filter audit rows"
            />
            <span className="audit-count">
              {view.length} of {rows.length} row{rows.length === 1 ? "" : "s"}
            </span>
          </div>

          <div className="glass" style={{ marginTop: 14, padding: 6, overflowX: "auto" }}>
            <table className="audit">
              <thead>
                <tr>
                  <th className="sortable" onClick={() => toggleSort("audit_id")}>Audit ID{arrow("audit_id")}</th>
                  <th className="sortable" onClick={() => toggleSort("timestamp")}>Time{arrow("timestamp")}</th>
                  <th className="sortable" onClick={() => toggleSort("customer_id")}>Customer{arrow("customer_id")}</th>
                  <th className="sortable" onClick={() => toggleSort("action")}>Action{arrow("action")}</th>
                  <th>Logistics</th>
                  <th>Amount</th>
                  <th>Email subject</th>
                </tr>
              </thead>
              <tbody>
                {view.map((r, i) => (
                  <tr key={`${r.audit_id}-${i}`}>
                    <td>{r.audit_id}</td>
                    <td>{when(r.timestamp)}</td>
                    <td>{r.customer_id}</td>
                    <td>{r.action}</td>
                    <td>{r.refund_type === "NONE" ? "-" : r.refund_type}</td>
                    <td>{amount(r)}</td>
                    <td>{r.email?.subject ?? "-"}</td>
                  </tr>
                ))}
                {view.length === 0 && (
                  <tr>
                    <td colSpan={7} className="audit-empty">No rows match "{filter}".</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

import type { EconomistOut } from "../types";
import { Badge } from "./Badge";
import { ACTION_SEVERITY, ACTION_LABEL, REFUND_TYPE_LABEL } from "../constants";

export function EconomistCard({ e }: { e: EconomistOut }) {
  return (
    <div className="glass card">
      <h3><span className="stage-no">3</span>Economist · Decision</h3>
      <div className="kv">
        <span className="k">Action</span>
        <Badge label={ACTION_LABEL[e.action] ?? e.action} severity={ACTION_SEVERITY[e.action] ?? "neutral"} />
      </div>
      {e.action === "REFUND" && (
        <div className="kv">
          <span className="k">Logistics</span>
          <span className="v">{REFUND_TYPE_LABEL[e.refund_type] ?? e.refund_type}</span>
        </div>
      )}
      {e.coupon_percent > 0 && (
        <div className="kv">
          <span className="k">Coupon</span>
          <span className="v">{e.coupon_percent}%</span>
        </div>
      )}
      {e.wallet_credit > 0 && (
        <div className="kv">
          <span className="k">Wallet credit</span>
          <span className="v">AED {e.wallet_credit}</span>
        </div>
      )}
      <div className="kv">
        <span className="k">Escalated</span>
        <span className="v" style={{ color: e.escalate ? "var(--c-alert)" : "var(--ink)" }}>
          {e.escalate ? "Yes — human review" : "No"}
        </span>
      </div>
      <p className="reason">{e.reason}</p>
    </div>
  );
}

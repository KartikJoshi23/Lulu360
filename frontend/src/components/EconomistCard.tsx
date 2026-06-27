import type { EconomistOut } from "../types";
import { Badge } from "./Badge";
import { WhyBox } from "./WhyBox";
import { ACTION_SEVERITY, ACTION_LABEL, REFUND_TYPE_LABEL } from "../constants";
import { ruleTrace, wasEscalationOverride } from "../ruleTrace";

export function EconomistCard({ e }: { e: EconomistOut }) {
  const trace = ruleTrace(e.reason);
  const escalated = wasEscalationOverride(e.reason);

  return (
    <div className="glass card">
      <h3><span className="stage-no">3</span>Economist / Decision</h3>

      {(trace || escalated) && (
        <div className="rule-trace" title="Which decision rule fired (derived from the engine's reason)">
          {trace && (
            <span className="rule-tag">
              <span className="rule-id">{trace.id}</span>
              {trace.label}
            </span>
          )}
          {escalated && (
            <span className="rule-tag override">
              <span className="rule-id">Valve</span>
              Escalation override
            </span>
          )}
        </div>
      )}

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
          {e.escalate ? "Yes - human review" : "No"}
        </span>
      </div>

      <WhyBox title="Why this decision?">
        {trace && (
          <div className="why-factors">
            <div className="why-row">
              <span className="why-k">Rule fired</span>
              <span className="why-v"><b>{trace.id}</b> — {trace.label}</span>
            </div>
          </div>
        )}
        {trace && <p className="why-narrative">{trace.detail}</p>}
        {escalated && (
          <p className="why-narrative" style={{ color: "var(--c-alert)" }}>
            The escalation valve then overrode the proposed action: high stakes met low certainty, so the case was handed to a human.
          </p>
        )}
        <p className="why-narrative why-engine">Engine note: {e.reason}</p>
      </WhyBox>
    </div>
  );
}

import type { InvestigatorOut } from "../types";
import { Badge } from "./Badge";
import { FlagChips } from "./FlagChips";
import { GENUINENESS_SEVERITY, CLAIM_SEVERITY } from "../constants";

export function InvestigatorCard({ v }: { v: InvestigatorOut }) {
  return (
    <div className="glass card">
      <h3><span className="stage-no">2</span>Investigator / Trust verdict</h3>
      <div className="kv">
        <span className="k">Genuineness</span>
        <Badge label={v.genuineness} severity={GENUINENESS_SEVERITY[v.genuineness] ?? "neutral"} />
      </div>
      <div className="kv">
        <span className="k">Claim status</span>
        <Badge label={v.claim_status} severity={CLAIM_SEVERITY[v.claim_status] ?? "neutral"} />
      </div>
      <FlagChips flags={v.flags} />
      <p className="reason">{v.reason}</p>
    </div>
  );
}

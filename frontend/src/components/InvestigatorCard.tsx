import type { InvestigatorOut } from "../types";
import { Badge } from "./Badge";
import { FlagChips } from "./FlagChips";
import { WhyBox, WhyFactor } from "./WhyBox";
import { GENUINENESS_SEVERITY, CLAIM_SEVERITY } from "../constants";

type Signals = {
  ratio?: number;
  kept?: number;
  burst?: number;
  age?: number;
  first_purchase?: boolean;
  prior_contacts?: number;
  promise_logged?: boolean;
};

export function InvestigatorCard({ v }: { v: InvestigatorOut }) {
  const s = (v.signals ?? null) as Signals | null;

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

      <WhyBox title="Why this verdict?">
        {s && (
          <div className="why-factors">
            <WhyFactor
              label="Refund-to-order ratio"
              value={`${s.ratio?.toFixed(2) ?? "—"}${ratioTag(s.ratio)}`}
              tone={ratioTone(s.ratio)}
            />
            <WhyFactor
              label="Account age"
              value={`${s.age ?? 0} months${(s.age ?? 0) <= 2 ? " · new" : " · established"}`}
              tone={(s.age ?? 0) <= 2 ? "warn" : "good"}
            />
            <WhyFactor label="Items kept after refund" value={`${s.kept ?? 0}`} tone={(s.kept ?? 0) > 0 ? "warn" : "good"} />
            <WhyFactor label="Complaints (last 30 days)" value={`${s.burst ?? 0}`} tone={(s.burst ?? 0) >= 3 ? "warn" : "good"} />
            <WhyFactor label="Prior contact on this issue" value={(s.prior_contacts ?? 0) > 0 ? `${s.prior_contacts}` : "None"} />
            <WhyFactor
              label="Logged promise on file"
              value={s.promise_logged ? "Yes — our record" : "None"}
              tone={s.promise_logged ? "good" : undefined}
            />
          </div>
        )}
        <p className="why-narrative">{v.reason}</p>
      </WhyBox>
    </div>
  );
}

function ratioTag(r?: number): string {
  if (r == null) return "";
  if (r >= 0.5) return " · high";
  if (r >= 0.3) return " · elevated";
  return " · low";
}
function ratioTone(r?: number): "good" | "warn" | "bad" | undefined {
  if (r == null) return undefined;
  if (r >= 0.5) return "bad";
  if (r >= 0.3) return "warn";
  return "good";
}

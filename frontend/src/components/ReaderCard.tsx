import type { ReaderOut } from "../types";
import { ConfidenceGauge } from "./ConfidenceGauge";

export function ReaderCard({ reader }: { reader: ReaderOut }) {
  return (
    <div className="glass card">
      <h3><span className="stage-no">1</span>Reader · Understanding</h3>
      <div className="kv">
        <span className="k">Issue type</span>
        <span className="v">{reader.issue_type.replace(/_/g, " ")}</span>
      </div>
      <div className="kv">
        <span className="k">Frustration</span>
        <span className="v">{reader.frustration}</span>
      </div>
      <ConfidenceGauge value={reader.confidence} />
    </div>
  );
}

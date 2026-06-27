import type { ResolveResponse } from "../types";
import { ACTION_LABEL } from "../constants";

/** A compact, colour-coded rail that makes the one-direction pipeline visible:
 *  Reader -> Investigator -> Economist -> Voice. Each node shows the single most
 *  important value that stage produced, and lights up in sequence on mount. */
export function PipelineFlow({ result }: { result: ResolveResponse }) {
  const nodes = [
    { n: 1, name: "Reader",       accent: "var(--c-reader)",       value: result.reader.issue_type.replace(/_/g, " ") },
    { n: 2, name: "Investigator", accent: "var(--c-investigator)", value: result.investigator.genuineness.replace(/_/g, " ") },
    { n: 3, name: "Economist",    accent: "var(--c-economist)",    value: ACTION_LABEL[result.economist.action] ?? result.economist.action },
    { n: 4, name: "Voice",        accent: "var(--c-voice)",        value: result.email_fired ? "Reply + email" : "Reply" },
  ];

  return (
    <div className="flow" role="img" aria-label="Pipeline data flow from Reader to Investigator to Economist to Voice">
      {nodes.map((nd, i) => (
        <div className="flow-seg" key={nd.name} style={{ ["--accent" as string]: nd.accent }}>
          {i > 0 && <span className="flow-arrow" aria-hidden="true" />}
          <div className="flow-node" style={{ animationDelay: `${0.08 + i * 0.12}s` }}>
            <span className="flow-no">{nd.n}</span>
            <span className="flow-text">
              <span className="flow-name">{nd.name}</span>
              <span className="flow-value">{nd.value}</span>
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

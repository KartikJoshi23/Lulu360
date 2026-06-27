import type { ResolveResponse } from "../types";
import { PipelineFlow } from "./PipelineFlow";
import { ReaderCard } from "./ReaderCard";
import { InvestigatorCard } from "./InvestigatorCard";
import { EconomistCard } from "./EconomistCard";
import { VoiceCard } from "./VoiceCard";
import { EmailPanel } from "./EmailPanel";

export function ResultsPanel({ result }: { result: ResolveResponse }) {
  return (
    <>
      <PipelineFlow result={result} />
      <div className="results">
        <ReaderCard reader={result.reader} />
        <InvestigatorCard v={result.investigator} />
        <EconomistCard e={result.economist} />
        <VoiceCard voice={result.voice} />
        <div style={{ gridColumn: "1 / -1" }}>
          <EmailPanel result={result} />
        </div>
      </div>
    </>
  );
}

import type { VoiceOut } from "../types";
import { CopyButton } from "./CopyButton";

export function VoiceCard({ voice }: { voice: VoiceOut }) {
  return (
    <div className="glass card">
      <h3>
        <span className="stage-no">4</span>Voice / Generated reply
        <span className="h3-actions"><CopyButton text={voice.reply_text} label="Copy reply" /></span>
      </h3>
      <div className="bubble">{voice.reply_text}</div>
    </div>
  );
}

import type { VoiceOut } from "../types";

export function VoiceCard({ voice }: { voice: VoiceOut }) {
  return (
    <div className="glass card">
      <h3><span className="stage-no">4</span>Voice · Generated reply</h3>
      <div className="bubble">{voice.reply_text}</div>
    </div>
  );
}

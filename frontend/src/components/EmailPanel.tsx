import type { ResolveResponse } from "../types";
import { ACTION_LABEL } from "../constants";

export function EmailPanel({ result }: { result: ResolveResponse }) {
  const email = result.voice.email;
  const action = result.economist.action;

  if (!result.email_fired || !email) {
    return (
      <div className="glass card">
        <h3>Email</h3>
        <div className="kv" style={{ borderBottom: 0 }}>
          <span className="k">Status</span>
          <span className="v" style={{ color: "var(--c-neutral)" }}>
            No email - {ACTION_LABEL[action] ?? action} never emails
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="glass card">
      <h3>Email triggered</h3>
      <div className="email">
        <div className="email-head">
          <span>New message</span>
          <span className="sent-stamp">
            <span className="bdot" /> Sent{result.audit_id ? ` - ${result.audit_id}` : ""}
          </span>
        </div>
        <div className="email-body">
          <div className="em-row">To: {email.to}</div>
          <div className="em-row">
            Subject: <b style={{ color: "var(--ink)" }}>{email.subject}</b>
          </div>
          <pre>{email.body}</pre>
        </div>
      </div>
    </div>
  );
}

import type { ResolveResponse } from "../types";

export function EmailPanel({ result }: { result: ResolveResponse }) {
  const email = result.voice.email;

  if (!result.email_fired || !email) {
    return (
      <div className="glass card">
        <h3>Email</h3>
        <div className="kv" style={{ borderBottom: 0 }}>
          <span className="k">Status</span>
          <span className="v" style={{ color: "var(--c-neutral)" }}>
            ⛔ No email — “{result.economist.action}” never emails
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="glass card">
      <h3>
        Email triggered <span style={{ color: "var(--c-trust)" }}>✓ sent</span>
        {result.audit_id && (
          <span style={{ float: "right", color: "var(--ink-faint)", fontSize: 12 }}>
            audit {result.audit_id}
          </span>
        )}
      </h3>
      <div className="email">
        <div className="em-row">To: {email.to}</div>
        <div className="em-row">
          Subject: <b style={{ color: "var(--ink)" }}>{email.subject}</b>
        </div>
        <pre>{email.body}</pre>
      </div>
    </div>
  );
}

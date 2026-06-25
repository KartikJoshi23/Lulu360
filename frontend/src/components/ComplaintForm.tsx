import { useState } from "react";
import { DEMO_PRESETS } from "../api/client";

interface Props {
  loading: boolean;
  onResolve: (message: string, customerId: string) => void;
}

export function ComplaintForm({ loading, onResolve }: Props) {
  const [message, setMessage] = useState("The TV arrived with a cracked screen and will not turn on.");
  const [customerId, setCustomerId] = useState("C0018");

  function submit() {
    const m = message.trim();
    const c = customerId.trim();
    if (m && c) onResolve(m, c);
  }

  function loadPreset(p: { customer_id: string; message: string }) {
    setMessage(p.message);
    setCustomerId(p.customer_id);
    onResolve(p.message, p.customer_id);
  }

  return (
    <section className="glass">
      <div className="form-grid">
        <div className="field">
          <label htmlFor="msg">Complaint message</label>
          <textarea
            id="msg"
            className="input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe the customer's complaint…"
          />
        </div>
        <div className="side-col">
          <div className="field">
            <label htmlFor="cid">Customer ID</label>
            <input
              id="cid"
              className="input"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value.toUpperCase())}
              placeholder="C0018"
            />
          </div>
          <button className="btn" onClick={submit} disabled={loading}>
            {loading ? <><span className="spinner" /> Resolving…</> : "Resolve complaint"}
          </button>
        </div>
      </div>

      <div className="form-grid" style={{ paddingTop: 0 }}>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label>Try a scenario</label>
          <div className="chips">
            {DEMO_PRESETS.map((p) => (
              <button key={p.customer_id} className="chip" onClick={() => loadPreset(p)} disabled={loading}>
                <b>{p.customer_id}</b> · {p.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

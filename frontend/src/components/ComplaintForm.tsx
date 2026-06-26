import { useEffect, useMemo, useState } from "react";
import { DEMO_PRESETS, getCustomers } from "../api/client";
import type { CustomerCatalogEntry } from "../types";

interface Props {
  loading: boolean;
  onResolve: (message: string, customerId: string) => void;
}

function snippet(s: string, n = 60) {
  return s.length > n ? s.slice(0, n).trimEnd() + "…" : s;
}

export function ComplaintForm({ loading, onResolve }: Props) {
  const [message, setMessage] = useState("The TV arrived with a cracked screen and will not turn on.");
  const [customerId, setCustomerId] = useState("C0018");

  // customer / message catalog for the picker
  const [catalog, setCatalog] = useState<CustomerCatalogEntry[]>([]);
  const [pickedId, setPickedId] = useState("");
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    let alive = true;
    getCustomers()
      .then((c) => alive && setCatalog(c))
      .catch(() => alive && setCatalog([]));
    return () => {
      alive = false;
    };
  }, []);

  const picked = useMemo(
    () => catalog.find((c) => c.customer_id === pickedId),
    [catalog, pickedId],
  );

  function selectCustomer(id: string) {
    setPickedId(id);
    setMsgIdx(0);
    const c = catalog.find((x) => x.customer_id === id);
    if (c && c.messages[0]) {
      setCustomerId(id);
      setMessage(c.messages[0].text);
    }
  }

  function selectMessage(i: number) {
    setMsgIdx(i);
    if (picked && picked.messages[i]) setMessage(picked.messages[i].text);
  }

  function submit() {
    const m = message.trim();
    const c = customerId.trim();
    if (m && c) onResolve(m, c);
  }

  function loadPreset(p: { customer_id: string; message: string }) {
    setMessage(p.message);
    setCustomerId(p.customer_id);
    setPickedId(p.customer_id);
    setMsgIdx(0);
    onResolve(p.message, p.customer_id);
  }

  return (
    <section className="glass">
      {/* --- pick any customer and load their real complaint --- */}
      {catalog.length > 0 && (
        <div className="picker">
          <div className="field">
            <label htmlFor="cust">Select a customer</label>
            <select
              id="cust"
              className="input"
              value={pickedId}
              onChange={(e) => selectCustomer(e.target.value)}
            >
              <option value="">— choose a customer ({catalog.length}) —</option>
              {catalog.map((c) => (
                <option key={c.customer_id} value={c.customer_id}>
                  {c.customer_id}
                  {c.loyalty_tier ? ` · ${c.loyalty_tier}` : ""} · {c.messages.length}{" "}
                  complaint{c.messages.length > 1 ? "s" : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="cmsg">Their complaint</label>
            <select
              id="cmsg"
              className="input"
              value={msgIdx}
              disabled={!picked}
              onChange={(e) => selectMessage(Number(e.target.value))}
            >
              {!picked && <option>— select a customer first —</option>}
              {picked?.messages.map((m, i) => (
                <option key={m.message_id} value={i}>
                  {m.issue_type.replace(/_/g, " ")} · {m.frustration} — “{snippet(m.text)}”
                </option>
              ))}
            </select>
            {picked && (
              <div className="hint">
                Loaded their real message — edit it below if needed, then Resolve.
              </div>
            )}
          </div>
        </div>
      )}

      {/* --- the message + id + action --- */}
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

      {/* --- quick scenarios --- */}
      <div className="form-grid" style={{ paddingTop: 0 }}>
        <div className="field" style={{ gridColumn: "1 / -1" }}>
          <label>Quick scenarios</label>
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

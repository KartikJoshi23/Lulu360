const MODULES = [
  { n: "1", name: "Reader", kind: "LSTM / NLU", desc: "Classifies the case issue type and frustration from the raw message." },
  { n: "2", name: "Investigator", kind: "Trust rules", desc: "Judges genuineness and verifies claims from account history, not tone." },
  { n: "3", name: "Economist", kind: "Decision rules", desc: "Chooses a fair, economically sound resolution and whether to escalate." },
  { n: "4", name: "Voice", kind: "FLAN-T5 / NLG", desc: "Writes the customer reply and triggers email plus audit logging on money actions." },
];

export function AboutPage() {
  return (
    <div className="container page">
      <h1 className="h1">About LuluCare 360</h1>
      <p className="sub">
        A four-module AI customer-care co-pilot for a Lulu-style hypermarket. The system reads
        the message, checks account history, applies transparent decision rules, and writes a
        customer-safe reply.
      </p>

      <div className="results">
        {MODULES.map((m) => (
          <div key={m.n} className="glass card">
            <h3>
              <span className="stage-no">{m.n}</span>
              {m.name} / <span style={{ color: "var(--ink-faint)", marginLeft: 4 }}>{m.kind}</span>
            </h3>
            <p className="reason" style={{ fontSize: 13.5 }}>{m.desc}</p>
          </div>
        ))}
      </div>

      <div className="glass notice" style={{ marginTop: 16 }}>
        MAIB / NLP and NLG Dialogue Systems / SP Jain School of Global Management, Dubai.
        All customer data is synthetic.
      </div>
    </div>
  );
}

# Demo Script — LuluCare 360 (5–7 min)

**Setup:** backend on `:8000` (`uvicorn backend.api.main:app`) and frontend on
`:5173` (`npm run dev`), or the Netlify site in demo mode. Open the **Demo** tab.
Point out the **health pill** (top-right) — `LSTM live` when the model artifacts
are loaded.

---

## 1. The genuine high-value customer (C0018) — show a refund + email firing
Pick the **"C0018 · Platinum · cracked TV"** chip (message: *"The TV arrived with
a cracked screen and will not turn on."*).

Walk the four cards left-to-right:
- **Reader** → `Damaged_Defective`, confidence gauge near full.
- **Investigator** → **GENUINE** (teal), `UNVERIFIED` — judged from clean history, not the calm tone.
- **Economist** → **Refund**, **Courier pickup** (resale ≥ 2000), not escalated.
- **Voice** → warm reply confirming the refund.
- **Email panel** → ✅ **sent** to `C0018@example.com`, with an audit id.

> Talking point: *calm does not mean undeserving* — Rule 5 refunds a genuine
> defect before any frustration rule, so a quiet Platinum customer is protected.

## 2. The serial abuser (C0001) — show the polite refusal, no email
Pick the **"C0001 · Serial refunder"** chip (an angry, demanding message).

- **Investigator** → **LIKELY_ABUSER** (red badge) with flag chips (high refund ratio).
- **Economist** → **Acknowledge**, no coupon/credit, not escalated.
- **Voice** → courteous reply that **promises nothing**.
- **Email panel** → ⛔ **no email** ("ACKNOWLEDGE never emails").

> Talking point: *trust comes from history, not tone.* The angriest message of
> all earns nothing because the records show the gaming (Rule 3 short-circuits
> before value/frustration).

## 3. (Optional) The escalation valve (C0059)
A SUSPICIOUS, high-order-value case with low Reader confidence → **Escalate**
(red), no email. Shows the human-in-the-loop valve that keeps the automation
rate honest.

---

## Close with the numbers
- Switch to the **Audit Log** tab → the **Stats card**: **automation rate 90.9%**,
  resolved / escalated / emails sent, and the table of every money action.
- One line each:
  - **Understanding → judging → writing**: LSTM reads, rules judge, FLAN-T5 (or
    template) writes.
  - **RNN vs LSTM**: the LSTM wins on long messages (vanishing-gradient) — see
    `Module1_The_Reader.ipynb`.
  - **The balance**: 90.9% automation trades revenue vs retention vs team time;
    only the high-stakes/low-certainty case escalates.
  - **Ethics**: a human overrides on ESCALATE, on a promise to an abuser, and on
    low confidence — see `docs/trust_memo.md`.

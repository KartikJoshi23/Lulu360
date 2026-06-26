<div align="center">

# 🛒 LuluCare 360
### An AI Complaint-Resolution Co-Pilot

**A four-module AI pipeline that *reads* a customer complaint, *judges* the customer's history, *decides* a fair resolution, and *writes* the reply — sending a confirmation email and logging every money action, all transparently.**

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-LSTM-FF6F00?logo=tensorflow&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![Tests](https://img.shields.io/badge/tests-120%20passing-2dd4bf)
![Automation](https://img.shields.io/badge/automation%20rate-90.9%25-2dd4bf)

</div>

---

## 👥 Team

**This project is made by:**

> **Gagandeep Singh · Kartik Joshi · Anish Borkar · Neha Thapa · Harsh Verma · Tanishk Verma · Zedan Parol**

**Institution:** SP Jain School of Global Management
**Programme:** Master of AI in Business (MAIB)
**Course:** Natural Language Processing — NLG & Dialogue Systems

> All customer data in this project is **synthetic** and was generated for teaching purposes. "LuluCare 360" is a fictional training exercise and is not affiliated with or endorsed by Lulu Group.

---

## 📋 Table of Contents

1. [What This Project Is](#-what-this-project-is)
2. [The Business Problem](#-the-business-problem)
3. [Why It's a Hard AI Problem](#-why-its-a-hard-ai-problem)
4. [Architecture](#-architecture)
5. [The Four Modules](#-the-four-modules)
6. [The Datasets](#-the-datasets)
7. [Interface Contracts](#-interface-contracts)
8. [The Dashboard](#-the-dashboard)
9. [Backend API](#-backend-api)
10. [Repository Structure](#-repository-structure)
11. [Running It Locally](#-running-it-locally)
12. [Testing & the 11 Handbook Cases](#-testing--the-11-handbook-cases)
13. [Deployment](#-deployment)
14. [Design Principles & Anti-Abuse Safeguards](#-design-principles--anti-abuse-safeguards)
15. [Tech Stack](#-tech-stack)

---

## 🎯 What This Project Is

LuluCare 360 is a **production-shaped AI complaint-resolution system** for a Lulu-style hypermarket. A customer's complaint message and their `customer_id` go in; a structured, fair, auditable resolution comes out — together with a natural-language reply and, when money is involved, a confirmation email.

The system is deliberately built as **four cooperating intelligences**, because a real AI system is rarely a single model:

```
[ message + customer_id ]
        │
        ▼
  ① READER  (LSTM)            → what is the issue, and how upset are they?
        │
        ▼
  ② INVESTIGATOR (rules)      → are they genuine, or gaming us?
        │
        ▼
  ③ ECONOMIST (rules)         → what is fair AND economically sensible?
        │
        ▼
  ④ VOICE (FLAN-T5 / template)→ write the reply, fire the email, log it
        │
        ▼
  [ consolidated decision → React dashboard ]
```

The neural net **reads**, the transparent rules **judge**, the pre-trained model **writes and acts** — and a human supervisor can see every step.

---

## 💼 The Business Problem

The VP of Customer Experience ("Reem") has two kinds of complaint that pull in opposite directions:

- **The genuinely wronged customer.** Their fresh order arrived spoiled; their new TV showed up cracked. They deserve a fast, fair, generous resolution — and many are the highest-spending, most loyal customers. Losing them is the most expensive thing the business does.
- **The serial abuser.** They have learned that complaining loudly enough gets a refund. They report every electronics item as defective, keep it, and get their money back. The old system *rewards* them, because a refund "feels cheaper than an argument."

LuluCare 360 must **tell these two apart** and then decide what is fair and economically sane for each — generous and instant for the genuine customer, a polite acknowledgement (and no payout) for the abuser — and send the confirmation email automatically when a remedy is granted.

---

## 🧠 Why It's a Hard AI Problem

Every complaint needs **three different kinds of intelligence**:

| Question | Where the answer lives | Module | AI type |
|---|---|---|---|
| *What are they upset about, and how upset?* | the **words** of the message | Reader | LSTM (NLU) |
| *Are they genuine, or gaming us?* | their **account history** | Investigator | transparent rules |
| *What resolution is fair and economical?* | verdict + **hard economics** | Economist | transparent rules |
| *How do we say it, and act on it?* | the **decision** | Voice | FLAN-T5 (NLG) |

> **The core insight:** a fraudster writes the angriest, most convincing message of all. The truth is in their *history*, not their *words*. The system never lets tone substitute for trust. The dataset is statistically verified so that **genuineness is independent of frustration** — the system cannot cheat by assuming "angry = deserving."

---

## 🏗 Architecture

```
                        ┌──────────────────────────────────────┐
  Customer complaint    │            REACT DASHBOARD           │
  + customer_id ───────▶│  pick a customer → see all 4 stages  │
                        │  + email + audit trail + KPIs        │
                        └──────────────────┬───────────────────┘
                                           │ POST /resolve  (HTTPS)
                                           ▼
                        ┌──────────────────────────────────────┐
                        │            FASTAPI BACKEND           │
  messages.csv ────────▶│  ① Reader   (LSTM, loaded at start)  │
  customers.csv ───────▶│  ② Investigator (history rules)      │
                        │  ③ Economist (economics rules)       │
                        │  ④ Voice (FLAN-T5 → template)        │
                        │  audit_log.jsonl ◀── every money act │
                        └──────────────────────────────────────┘

  Netlify (static React)  ──HTTPS──▶  Render/Railway (Python API)
```

**Why the split?** Netlify cannot run a persistent Python process or hold a TensorFlow model in memory. So the React bundle is served statically from Netlify, and the Python API (Reader inference + both rule engines + Voice) is hosted separately on Render/Railway, called over HTTPS.

---

## 🔧 The Four Modules

### ① The Reader — `backend/modules/reader/reader.py`
An **LSTM-based NLU front door**. Two small Keras LSTM classifiers share a tokenizer:
- **Issue classifier** — 7 classes: `Delivery, Damaged_Defective, Refund_Return, Billing, Product_Quality, App_Technical, General_Query`
- **Frustration classifier** — 3 classes: `Low, Medium, High`
- Trained **only** on `messages.csv` text (never the customer history) — `train_reader.py` produces the artifacts in `backend/models/`.
- The notebook (`Module1_The_Reader.ipynb`) also runs the **SimpleRNN vs LSTM** experiment, showing the LSTM wins on longer messages (the vanishing-gradient lesson).
- **Hybrid & resilient:** if the trained `.keras` artifacts are present it uses the real LSTM; otherwise it falls back to a deterministic keyword classifier that honours the same contract — so the pipeline always runs, even on a host without TensorFlow.

```python
read_message(text) -> {"issue_type": str, "frustration": str, "confidence": float}
```

### ② The Investigator — `backend/modules/investigator/investigator.py`
A **transparent trust engine** — no model, every decision readable and defensible.
- **Genuineness** from *history alone* (refund-to-order ratio, items kept after refund, recent complaint burst, account age). **Tone-blind by design** — it never reads frustration or the message text.
- **Claim verification** — cross-examines "your rep promised me a refund" against *our own* records (`prior_promise_logged`, `prior_contacts_this_issue`, and the free-text agent notes, with negation-aware matching).
- Re-running its rules over the real data reproduces the ground-truth label for **218 / 220** customers.

```python
investigate(reader_output, profile, conversation_history=None)
  -> {"genuineness": ..., "claim_status": ..., "reason": ..., (+ signals, flags, confidence)}
```

### ③ The Economist — `backend/modules/economist/economist.py`
A **text-free, pure-economics rule engine**. Fuses trust + value + economics into one decision.
- `value_band` — HIGH / MEDIUM / LOW from CLV + tier (value scales a remedy, never *grants* trust).
- `choose_action` — an **8-rule remediation tier table**, evaluated top-to-bottom (the order *is* the anti-abuse precedence).
- `refund_logistics` — keep-vs-pickup economics (perishable → keep; high resale → pickup; freight > resale → keep).
- `should_escalate` — fires only on (large money + suspicious trust) or (low confidence + high value).

```python
decide(verdict, reader_output, profile)
  -> {"action", "refund_type", "coupon_percent", "wallet_credit",
      "escalate", "email_trigger", "reason"}
```

### ④ The Voice — `backend/modules/voice/voice.py`
The **NLG + email + audit** layer.
- `generate_reply` — drafts the customer reply with **FLAN-T5**, with a deterministic **template fallback** (and a quality gate) so a reply always renders and the decision is never affected by model latency.
- `fire_email` — composes a **full, self-contained confirmation email** (greeting, the concrete remedy + timeline, a reference number, and a sign-off) and appends one row to the **append-only audit log** — but **only** for `COUPON / REFUND / WALLET_CREDIT`. `ACKNOWLEDGE` and `ESCALATE` never email.
- **Decision-preserving:** the Voice reads `email_trigger`; it never recomputes it.

---

## 📊 The Datasets

Two synthetic CSVs (in `dataset/`, mirrored to `backend/data/` for the runtime), joined on `customer_id`:

**`messages.csv` — 630 × 5** · perfectly balanced: 90 per issue type, 210 per frustration level, exactly 30 in every issue×frustration cell. Mean length 14 words (max 23), so `MAXLEN=40` truncates nothing. 205 distinct customers referenced.

**`customers.csv` — 220 × 21** · the history an abuser cannot fake: `refund_to_order_ratio`, `items_kept_after_refund`, `complaints_last_30_days`, `account_age_months`, `loyalty_tier`, `clv_estimate`, `order_value`, `is_perishable_or_hygiene`, `resale_value`, `reverse_logistics_cost`, `prior_promise_logged`, `customer_care_notes`, and more.
- Mix: **120 GENUINE · 55 SUSPICIOUS · 45 LIKELY_ABUSER**
- ⚠️ The 21st column `_archetype` is the **ground-truth label** — a leakage trap. Every loader **drops it on load**; it is read only inside tests to score the Investigator, and never appears in any module input or API response.

---

## 📜 Interface Contracts

All four modules communicate through **frozen dictionary contracts**, with all string values imported from a single source (`shared/enums.py`, mirrored byte-for-byte in `shared/enums.js`). The consolidated response the dashboard consumes:

```jsonc
{
  "customer_id": "C0018",
  "message": "The TV arrived with a cracked screen…",
  "reader":       { "issue_type", "frustration", "confidence" },
  "investigator": { "genuineness", "claim_status", "reason", "signals", "flags", "confidence" },
  "economist":    { "action", "refund_type", "coupon_percent",
                    "wallet_credit", "escalate", "email_trigger", "reason" },
  "voice":        { "reply_text", "email": { "to", "subject", "body" } | null },
  "email_fired":  true,
  "audit_id":     "A0033",
  "automation":   { "escalated": false }
}
```

> Every value is a **native, JSON-safe Python type** — pandas/NumPy scalars are cast before they cross a boundary, so nothing breaks the React layer. Pydantic models for every contract live in `shared/schemas.py`.

---

## 🖥 The Dashboard

A modern, **dark glassmorphism** dashboard (React 18 + TypeScript + Vite). Top navigation (not a sidebar): **Demo · Audit Log · About**, with a live health pill showing whether the real LSTM or keyword fallback is serving.

**Demo page**
- **KPI cards** at the top — automation rate, resolved, escalated, emails sent.
- **Customer / message picker** — select **any** of the 205 customers (with their tier and complaint count); their **real complaint(s)** from `messages.csv` load into the box (a second dropdown picks among a customer's multiple complaints). The message stays editable.
- **Four pipeline-stage cards**, colour-coded by severity:
  1. **Reader** — issue type, frustration, an animated confidence gauge.
  2. **Investigator** — genuineness & claim badges (teal = trust, amber = caution, red = alert), fraud flags, reasoning.
  3. **Economist** — action badge + refund logistics / coupon % / wallet credit / escalation flag.
  4. **Voice** — the generated reply as a chat bubble.
- **Email panel** — a clear sent/none indicator, with the full composed email and its audit reference.

**Audit Log page** — every money action in a table (id, time, customer, action, logistics, amount, subject), with the KPI cards.

**Demo mode** — set `VITE_DEMO_MODE=true` and the dashboard serves precomputed responses from `frontend/src/demoData.ts`, so it demonstrates fully even with no backend running.

---

## 📡 Backend API

FastAPI service (`backend/api/main.py`). Interactive docs at `/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/resolve` | Run the full pipeline → consolidated response |
| `GET` | `/health` | `{ status, reader_backend, flan_enabled }` |
| `GET` | `/stats` | Automation rate + action breakdown |
| `GET` | `/audit` | The money-action audit trail |
| `GET` | `/customers` | Customer + message catalog for the picker |

```bash
curl -X POST http://localhost:8000/resolve \
  -H "Content-Type: application/json" \
  -d '{"message":"The TV arrived with a cracked screen","customer_id":"C0018"}'
```

---

## 📁 Repository Structure

```
lulucare360/
├── README.md  ·  CLAUDE.md  ·  DEPLOY.md  ·  render.yaml  ·  .gitignore
│
├── backend/
│   ├── api/main.py              # FastAPI app (/resolve, /health, /stats, /audit, /customers)
│   ├── pipeline.py              # orchestrates Reader → Investigator → Economist → Voice
│   ├── stats.py                 # automation-rate telemetry
│   ├── data/
│   │   ├── customers.csv  messages.csv
│   │   ├── loader.py            # lookup_profile + message_catalog (drops _archetype)
│   │   └── generate_data.py     # synthetic data generator (seed=42)
│   ├── models/                  # trained Reader artifacts (git-ignored; rebuilt by train_reader.py)
│   ├── modules/
│   │   ├── reader/{reader.py, train_reader.py, Module1_The_Reader.ipynb}
│   │   ├── investigator/{investigator.py, profile_loader.py}
│   │   ├── economist/economist.py
│   │   └── voice/voice.py
│   ├── scripts/{gen_demo_data.py, handbook_report.py}
│   └── tests/{test_reader, test_investigator, test_economist, test_voice, test_pipeline}.py
│
├── frontend/                    # React 18 + TypeScript + Vite
│   ├── netlify.toml  .env.example  package.json
│   └── src/
│       ├── App.tsx  main.tsx  theme.css  types.ts  constants.ts
│       ├── api/client.ts        # live API + demo-mode fallback
│       ├── pages/{DemoPage, AuditPage, AboutPage}.tsx
│       └── components/          # TopNav, ComplaintForm (picker), Reader/Investigator/
│                                #   Economist/Voice cards, EmailPanel, StatsCard …
│
├── shared/                      # one source of truth for both languages
│   ├── enums.py  enums.js       # frozen string constants (byte-identical)
│   └── schemas.py               # pydantic contract models
│
├── dataset/                     # the provided source data (+ a README)
├── lulucare360_module3/         # Economist notebooks (enums, economist, tests)
├── docs/                        # steering context for Modules 1 & 3
└── plan/                        # the professor's Handbook + the Implementation Plan
```

---

## 🚀 Running It Locally

**Prerequisites:** Python 3.11+, Node 18+.

```bash
# 1) Backend
pip install -r backend/requirements.txt
python backend/modules/reader/train_reader.py     # optional: trains the LSTM (else keyword fallback)
uvicorn backend.api.main:app --reload --port 8000  # run from the repo root

# 2) Frontend (second terminal)
cd frontend
npm install
npm run dev                                        # http://localhost:5173
```

Open **http://localhost:5173**, pick a customer, and watch the complaint flow through all four modules.

**Useful environment variables**

| Variable | Where | Meaning |
|---|---|---|
| `VITE_API_BASE_URL` | frontend | Base URL of the Python API (default `http://127.0.0.1:8000`) |
| `VITE_DEMO_MODE` | frontend | `true` → serve precomputed responses, no backend needed |
| `LULU_DISABLE_FLAN` | backend | `1` → skip FLAN-T5, use the fast deterministic template generator |
| `LULU_FLAN_MODEL` | backend | FLAN model id (default `google/flan-t5-base`) |
| `NETLIFY_ORIGIN` | backend | Allowed CORS origin for the deployed site |

---

## 🧪 Testing & the 11 Handbook Cases

```bash
# Full backend suite (offline/deterministic)
LULU_DISABLE_FLAN=1 python -m pytest backend/tests/ -q          # → 120 passed

# Run the verified handbook cases through the assembled system + automation rate
python backend/scripts/handbook_report.py
```

**Coverage:** Reader contract, all Investigator fraud/claim paths (incl. the C0006 abuser-with-logged-promise conflict and negation-aware notes), the full Economist tier table + logistics + escalation, the Voice email rule + audit log, and an end-to-end pipeline contract test.

The **11 verified cases** (pinned to real `customers.csv` rows) and their expected resolutions:

| # | Customer | Scenario | Expected |
|---|---|---|---|
| 1 | C0005 | Gold · perishable · genuine defect | REFUND + KEEP_ITEM · email |
| 2 | C0013 | Electronics resale ≥ 2000 | REFUND + PICKUP · email |
| 3 | C0001 | Serial refunder (ratio 0.83), furious, high value | ACKNOWLEDGE · no email |
| 4 | C0004 | Unverified "promise" claim | ACKNOWLEDGE · no email |
| 5 | C0034 | Genuine + CONFIRMED logged promise · perishable | REFUND + KEEP_ITEM · email |
| 6 | C0032 | resale 164 < freight 180 | REFUND + KEEP_ITEM (economics) |
| 7 | C0016 | First purchase, suspicious | COUPON 20% · no escalate |
| 8 | C0020 | Bronze, low value, low frustration | ACKNOWLEDGE · no email |
| 9 | C0059 | Suspicious + large order + low confidence | **ESCALATE** · no email |
| 10 | C0018 | Platinum, **calm**, genuine defect (trap) | REFUND + PICKUP · email |
| 11 | C0006 | Abuser **with** a logged promise | REFUND + PICKUP + ABUSE_FLAG · email |

**Result: 11 / 11 correct.** Only case 9 escalates by design →

```
automation_rate = (cases where action ≠ ESCALATE) / total = 10 / 11 = 90.9%  (target ≥ 90%)
```

---

## 🌐 Deployment

Full steps in **[DEPLOY.md](DEPLOY.md)**. In short:

- **Frontend → Netlify** (`frontend/netlify.toml`): build `npm run build`, publish `dist`, SPA redirect. Set `VITE_API_BASE_URL` to the live API.
- **Backend → Render** (`render.yaml` + `backend/requirements-deploy.txt`): a lightweight image (template Voice + keyword Reader, no torch/TF) that fits a free tier; start `uvicorn backend.api.main:app`. Set `NETLIFY_ORIGIN` for CORS.
- **Static demo fallback:** `VITE_DEMO_MODE=true` serves precomputed responses, so the dashboard demos even if the API is asleep.

---

## 🛡 Design Principles & Anti-Abuse Safeguards

- **Trust comes from history, not tone.** The Investigator never reads frustration or the message.
- **Abuse never pays.** A `LIKELY_ABUSER` short-circuits to `ACKNOWLEDGE` before any value/frustration rule.
- **Unverified ≠ payout.** "Your rep promised me a refund" is never honoured unless *our* records confirm it.
- **A logged promise is honoured — but capped** (even for an abuser; flagged for human review).
- **Calm never downgrades a genuine defect.** A Platinum customer's calm cracked-TV still gets a full refund.
- **Escalate sparingly.** Over-escalation destroys the automation business case; the valve fires on just two conditions.
- **Email only on money actions.** Set once by the Economist, obeyed by the Voice, never recomputed.
- **Everything auditable.** Every coupon/refund/credit writes an append-only audit row, surfaced in the dashboard.
- **No leakage.** `_archetype` is dropped on load and quarantined to tests.

---

## 🧰 Tech Stack

**Backend:** Python · FastAPI · Uvicorn · Pydantic · pandas · TensorFlow/Keras (Reader LSTM) · Hugging Face Transformers + PyTorch (FLAN-T5 Voice) · pytest · ruff
**Frontend:** React 18 · TypeScript · Vite · CSS (dark glassmorphism, no UI framework)
**Infra:** Netlify (frontend) · Render / Railway (backend) · GitHub

---

<div align="center">

**Built for MAIB · NLP — NLG & Dialogue Systems · SP Jain School of Global Management**

*LuluCare 360 reads with a neural network, judges with transparent rules, replies with a pre-trained generator, and acts by sending the email — because real AI combines learned language understanding with explicit, accountable decisions about money and trust.*

</div>

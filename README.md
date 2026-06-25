

# 🛒 LuluCare 360
### AI Complaint-Resolution Co-Pilot

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange?logo=tensorflow)](https://tensorflow.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Netlify](https://img.shields.io/badge/Deploy-Netlify-00C7B7?logo=netlify)](https://netlify.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MAIB](https://img.shields.io/badge/SP%20Jain-MAIB%20NLP%20Project-purple)](https://spjain.org)

**A four-module AI pipeline that reads a complaint, judges the customer's history, decides a fair resolution, and writes the reply — all transparently, with full audit logging.**

*MAIB · Natural Language Processing & NLG/Dialogue Systems · SP Jain School of Global Management, Dubai*

[Architecture](#-architecture) · [Modules](#-the-four-modules) · [Dataset](#-dataset) · [Setup](#-setup--installation) · [API](#-api-reference) · [Tests](#-testing) · [References](#-references)

</div>

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Architecture](#-architecture)
3. [The Four Modules](#-the-four-modules)
4. [Dataset](#-dataset)
5. [Interface Contracts](#-interface-contracts)
6. [Module 3 — The Economist (Our Module)](#-module-3--the-economist-our-module)
7. [Key Design Decisions & Traps](#-key-design-decisions--traps)
8. [Setup & Installation](#-setup--installation)
9. [Running the System](#-running-the-system)
10. [API Reference](#-api-reference)
11. [Testing](#-testing)
12. [File & Folder Structure](#-file--folder-structure)
13. [Deployment](#-deployment)
14. [Automation Rate & Trust Memo Highlights](#-automation-rate--trust-memo-highlights)
15. [Team & Contributions](#-team--contributions)
16. [References](#-references)

---

## 🎯 Project Overview

LuluCare 360 is a production-shaped AI complaint-resolution system built for **Lulu Hypermarket**, one of the largest retailers in the GCC. Millions of orders flow through Lulu every week, and with them a constant stream of customer complaints — from late deliveries to damaged electronics to billing disputes.

The system must answer **three fundamentally different questions** about every complaint:

| Question | Data Source | Module | AI Type |
|---|---|---|---|
| *What is the customer upset about, and how upset?* | Message text | **Reader** | LSTM (NLU) |
| *Is this customer genuine, or gaming us?* | Account history | **Investigator** | Transparent rules |
| *What resolution is fair and economically sensible?* | Verdict + economics | **Economist** | Transparent rules |
| *How do we write the reply and send the email?* | Decision | **Voice** | FLAN-T5 (NLG) |

> **The core insight:** A fraudster writes the angriest, most convincing message of all. The truth is in their *history*, not their *words*. The architecture deliberately separates these two information streams and never lets tone substitute for trust.

---

## 🏗 Architecture

```
                          ┌─────────────────────────────────────┐
  Customer                │          REACT FRONTEND             │
  Complaint ─────────────▶│  Stage 1: Message                   │
  + customer_id           │  Stage 2: Reader verdict            │
                          │  Stage 3: Investigator verdict      │
                          │  Stage 4: Economist decision        │
                          │  Stage 5: Voice reply               │
                          │  Stage 6: Email / Audit log         │
                          └──────────────┬──────────────────────┘
                                         │ POST /resolve
                                         ▼
                          ┌─────────────────────────────────────┐
                          │         FASTAPI BACKEND             │
                          │                                     │
  messages.csv ──────────▶│  ┌──────────┐                       │
  (LSTM training)         │  │  READER  │ issue_type            │
                          │  │  (LSTM)  │ frustration ─────┐    │
                          │  └──────────┘ confidence       │    │
                          │                                │    │
  customers.csv ─────────▶│  ┌─────────────────┐          │    │
  (history lookup)        │  │  INVESTIGATOR   │◀─────────┘    │
                          │  │  (trust rules)  │ genuineness   │
                          │  └────────────────┬┘ claim_status  │
                          │                   │                │
                          │  ┌────────────────▼┐               │
                          │  │   ECONOMIST     │ action        │
                          │  │  (econ rules)   │ refund_type   │
                          │  └────────────────┬┘ email_trigger │
                          │                   │                │
                          │  ┌────────────────▼┐               │
                          │  │     VOICE       │ reply_text    │
                          │  │   (FLAN-T5)     │ email_body    │
                          │  └─────────────────┘               │
                          │                                     │
                          │  audit_log.jsonl ◀── every         │
                          │                      money action   │
                          └─────────────────────────────────────┘

  Netlify (static React) ──HTTPS──▶ Render/Railway (Python API)
```

### Why the split?
Netlify cannot run a persistent Python process, hold a TensorFlow model in memory between requests, or train one. The Python backend (Reader training, model inference, rule engines) lives on a separately-hosted service (Render, Railway, or Hugging Face Spaces). Netlify serves only the compiled React bundle.

---

## 🔧 The Four Modules

### Module 1 — The Reader (LSTM)
**Owner:** NLP sub-team | **File:** `backend/modules/reader/reader.py`

Reads the raw complaint text and outputs its topic and emotional intensity.

- **Architecture:** Embedding → LSTM → two separate Dense/softmax heads
- **Task 1 (Issue Classification):** 7-class softmax — *Delivery, Damaged_Defective, Refund_Return, Billing, Product_Quality, App_Technical, General_Query*
- **Task 2 (Frustration Classification):** 3-class softmax — *Low, Medium, High*
- **Why LSTM, not bag-of-words?** `"I did not get my refund"` and `"I got my refund"` share every important word but mean opposite things. An LSTM reads the sequence one token at a time and carries memory across it.
- **Training data:** `messages.csv` — 630 messages, perfectly balanced, 30 per issue×frustration cell, mean length 14 words, `MAXLEN = 40` truncates nothing.
- **Experiment:** The plan requires a **SimpleRNN vs LSTM** comparison; the LSTM wins on longer messages due to the vanishing gradient problem.
- **Saved artifacts:** `reader_issue.keras`, `reader_frustration.keras`, `tokenizer.json`, `label_maps.json` in `backend/models/`.

### Module 2 — The Investigator (Trust Engine)
**Owner:** Trust sub-team | **File:** `backend/modules/investigator/investigator.py`

Transparent rule engine — no model. Every decision must be readable and defensible to a VP.

**Check 1 — Genuineness signals (from account history):**
| Signal | SUSPICIOUS threshold | LIKELY_ABUSER threshold |
|---|---|---|
| `refund_to_order_ratio` | ≥ 0.25 | ≥ 0.50 |
| `items_kept_after_refund` | ≥ 1 | ≥ 3 |
| `complaints_last_30_days` | ≥ 3 | ≥ 4 |
| `account_age_months` | ≤ 2 | — |

**Check 2 — Claim verification** (small NLP via keyword matching):
- Reads `prior_promise_logged`, `prior_contacts_this_issue`, and `customer_care_notes`
- Returns `CONFIRMED` / `CONTRADICTED` / `UNVERIFIED`
- **Rule:** A customer's claim that "your rep promised a refund" is `UNVERIFIED` unless *our own* notes corroborate it

> The Investigator is **tone-blind by design.** It never reads `frustration` or the raw message. Trust is computed from records alone.

### Module 3 — The Economist (Resolution Engine)
**Owner:** Krishna Mathur (AS25DXB018) + team | **File:** `backend/modules/economist/economist.py`

*See dedicated section below for full depth.*

### Module 4 — The Voice (FLAN-T5 + Email + UI)
**Owner:** Voice/Integration sub-team | **File:** `backend/modules/voice/voice.py`

Turns the structured decision into a natural-language reply.

- **Model:** `google/flan-t5-small` — follows instructions, so the Economist's decision becomes the prompt
- **Email trigger:** Fires a simulated email (+ audit log entry) for `COUPON`, `REFUND`, `WALLET_CREDIT` only — never for `ACKNOWLEDGE` or `ESCALATE`
- **Template fallback:** If FLAN-T5 is unavailable or slow, a deterministic template generator produces the reply so the pipeline never stalls
- **Integration owner:** The Voice sub-team owns `test_pipeline.py` and the final stitch
- **UI:** Gradio / React dashboard showing all 6 pipeline stages

---

## 📊 Dataset

Two synthetic CSVs, produced by `generate_data.py` (seed = 42). They join on `customer_id`.

### `messages.csv` — 630 × 5
| Column | Type | Notes |
|---|---|---|
| `message_id` | str | M0001–M0630 |
| `customer_id` | str | Foreign key to customers.csv |
| `text` | str | Complaint message, mean 14 words, max 23 |
| `issue_type` | str | 7 types, exactly **90 per type** |
| `frustration` | str | 3 levels, exactly **210 per level** |

**Balance guarantee:** Exactly **30 messages** in every `issue_type × frustration` cell. No oversampling needed.

### `customers.csv` — 220 × 21
| Column | Type | Notes |
|---|---|---|
| `customer_id` | str | C0001–C0220 |
| `account_age_months` | int | 0–72 months |
| `loyalty_tier` | str | Bronze (68) / Silver (70) / Gold (54) / Platinum (28) |
| `lifetime_spend` | int | AED |
| `total_orders` | int | |
| `total_complaints` | int | |
| `total_refunds_received` | int | |
| `refund_to_order_ratio` | float | Key fraud signal |
| `items_kept_after_refund` | int | Key fraud signal |
| `complaints_last_30_days` | int | Burst signal |
| `is_first_purchase` | bool | |
| `order_value` | int | AED, avg AED 7,958 |
| `product_category` | str | 10 categories |
| `is_perishable_or_hygiene` | bool | 110 customers |
| `resale_value` | int | AED |
| `reverse_logistics_cost` | int | AED |
| `prior_contacts_this_issue` | int | |
| `prior_promise_logged` | bool | 33 customers |
| `customer_care_notes` | str | All 220 have notes |
| `clv_estimate` | int | Annualised CLV, avg AED 48,066 |
| `_archetype` | str | ⚠️ **LEAKAGE TRAP** — drop on load, use only in tests |

**Archetype distribution:** 120 GENUINE · 55 SUSPICIOUS · 45 LIKELY_ABUSER

**Critical bias property:** Genuineness is statistically independent of frustration. An abuser is equally likely to write a calm or furious message. The system cannot cheat by treating anger as evidence of genuineness.

---

## 📜 Interface Contracts

All four modules communicate through these frozen dictionary contracts. **Keys are immutable** — renaming a key is a contract breach caught by schema tests.

```python
# Module 1 → Module 2, 3
reader_output = {
    "issue_type":  str,   # one of the 7 ISSUE_TYPES (TitleCase)
    "frustration": str,   # "Low" | "Medium" | "High"
    "confidence":  float  # [0.0, 1.0]
}

# Module 2 → Module 3
verdict = {
    "genuineness":  str,  # "GENUINE" | "SUSPICIOUS" | "LIKELY_ABUSER"
    "claim_status": str,  # "CONFIRMED" | "CONTRADICTED" | "UNVERIFIED"
    "reason":       str   # internal explanation
}

# Module 3 → Module 4  (the Economist output)
decision = {
    "action":         str,   # "ACKNOWLEDGE"|"COUPON"|"WALLET_CREDIT"|"REFUND"|"ESCALATE"
    "refund_type":    str,   # "PICKUP" | "KEEP_ITEM" | "NONE"
    "coupon_percent": int,   # 0 | 20 | 50
    "wallet_credit":  int,   # AED, 0 if not applicable
    "escalate":       bool,
    "email_trigger":  bool,  # True iff action in {COUPON, REFUND, WALLET_CREDIT}
    "reason":         str    # internal explanation — NOT a customer-facing sentence
}

# Module 4 → React (consolidated pipeline response)
response = {
    "reader":        reader_output,
    "verdict":       verdict,
    "decision":      decision,
    "reply_text":    str,    # customer-facing reply
    "email_subject": str | None,
    "email_body":    str | None,
    "audit_id":      str | None
}
```

> **All values must be JSON-safe native Python types.** pandas profiles return NumPy scalars by default — cast with `int()`, `float()`, `bool()`, `str()` before returning. An `np.bool_` leaking to the React layer causes silent serialization failures.

---

## 💰 Module 3 — The Economist (Our Module)

**File:** `backend/modules/economist/economist.py`  
**Notebook:** `economist.ipynb`  
**Tests:** `test_economist.ipynb` / `tests/test_economist.py`

The Economist is a **text-free, pure-economics rule engine.** It receives the Investigator's verdict, the Reader's output, and the customer profile, and outputs one structured decision. It never writes a customer-facing sentence — that is the Voice's job.

### The 5 Functions

#### 1. `value_band(p)` — Customer Value Classification
```
Platinum tier OR CLV ≥ AED 40,000  →  HIGH
Gold/Silver tier OR CLV ≥ AED 12,000  →  MEDIUM
Else  →  LOW
```
> Value never *grants* trust. It only *scales* remediation within an already-trusted path.

**Verified split:** 84 HIGH · 111 MEDIUM · 25 LOW across 220 customers.

#### 2. `refund_logistics(p)` — Keep vs Pickup Tree
```
if perishable/hygiene          →  KEEP_ITEM   (cannot resell; collecting is pure waste)
elif resale_value ≥ AED 2,000  →  PICKUP      (costly resalable; always recover)
elif freight > resale          →  KEEP_ITEM   (shipping back costs more than it's worth)
else                           →  PICKUP
```
**Verified split:** 114 KEEP_ITEM (110 perishable + 4 by cost economics) · 106 PICKUP.

#### 3. `should_escalate(verdict, reader, p, proposed_refund)` — Escalation Valve
| Condition | Escalate? |
|---|---|
| Proposed REFUND + SUSPICIOUS + `order_value > AED 5,000` | ✅ |
| Reader `confidence < 0.5` + value band = HIGH | ✅ |
| Anything else | ❌ |

> Use it sparingly. A system that escalates most cases leaves the team just as buried as before — and quietly destroys the automation business case.

#### 4. `choose_action(verdict, reader, p)` — The 8-Rule Remediation Tier Table

The anti-abuse precedence is **fixed**. Evaluate top-to-bottom; first match wins:

| Rule | Condition | Action |
|---|---|---|
| 1 | `claim_status == CONTRADICTED` | ACKNOWLEDGE — respond from record, deny remedy |
| 2 | `claim_status == CONFIRMED` | Honour exactly what was logged (REFUND or COUPON) |
| 3 | `genuineness == LIKELY_ABUSER` | ACKNOWLEDGE — abuse never pays, regardless of anger or value |
| 4 | `is_first_purchase` OR `account_age_months ≤ 2` | COUPON 20% — generous but capped |
| 5 | GENUINE + `Damaged_Defective` | REFUND (logistics decided by `refund_logistics`) |
| 6 | GENUINE + `High` frustration + HIGH value | COUPON 50% |
| 7 | GENUINE + `Medium` frustration | COUPON 20% (or WALLET_CREDIT for LOW-value) |
| 8 | Everything else (GENUINE, Low, routine) | ACKNOWLEDGE |

**Special case (C0006 conflict):** A `CONFIRMED` logged promise is honoured even for a `LIKELY_ABUSER` — it is *our* record, not the customer's claim. However, it is capped to the promised scope: no extra logistics generosity, no stacked remediation, and the abuse flag appears in `reason`.

#### 5. `decide(verdict, reader, p)` — Main Orchestrator
```python
action, coupon_percent, wallet_credit, note = choose_action(...)
refund_type  = refund_logistics(p) if action == REFUND else NONE
escalate     = should_escalate(...)
if escalate: action = ESCALATE          # overrides proposed action
email_trigger = action in EMAIL_ACTIONS  # recomputed AFTER escalation
return cast all values to native Python types
```

### Tunable Policy Knobs
| Knob | Value | Rationale |
|---|---|---|
| `COUPON_STANDARD` | 20% | Default goodwill gesture |
| `COUPON_GENEROUS` | 50% | High-frustration + HIGH-value retention |
| `WALLET_CREDIT_BY_BAND` | LOW: AED 50, MED: AED 100, HIGH: AED 200 | Flat AED credit, band-scaled |
| `NEW_ACCOUNT_MAX_MONTHS` | 2 months | "Newbie" threshold for generous-but-capped path |
| `HIGH_RESALE_THRESHOLD` | AED 2,000 | Electronics/appliances always worth recovering |
| `ESCALATE_ORDER_VALUE` | AED 5,000 | Large-money threshold for escalation valve |
| `LOW_CONFIDENCE` | 0.50 | Reader confidence floor for escalation |

### The 11 Verified Test Cases

| # | Customer | Scenario | Expected |
|---|---|---|---|
| 1 | C0005 | Gold · Fresh Produce (perishable) · GENUINE · Damaged_Defective | REFUND + KEEP_ITEM |
| 2 | C0013 | Silver · Electronics resale AED 34,890 · GENUINE · Damaged_Defective | REFUND + PICKUP |
| 3 | C0001 | Silver · ratio 0.833 · LIKELY_ABUSER · furious · CLV HIGH | ACKNOWLEDGE (abuse never pays) |
| 4 | C0004 | Silver · GENUINE · UNVERIFIED "promise" claim | ACKNOWLEDGE (unverified ≠ payout) |
| 5 | C0034 | Bronze · perishable · GENUINE · CONFIRMED logged promise | REFUND + KEEP_ITEM |
| 6 | C0032 | Silver · Fashion · resale AED 164 < freight AED 180 | REFUND + KEEP_ITEM (economics) |
| 7 | C0016 | Gold · first purchase · SUSPICIOUS | COUPON 20% · no escalate |
| 8 | C0020 | Bronze · CLV AED 4,959 · GENUINE · Low frustration | ACKNOWLEDGE |
| 9 | C0059 | Platinum · conf 0.45 · SUSPICIOUS · order AED 24,392 | ESCALATE |
| 10 | C0018 | Platinum · **CALM** · GENUINE · Damaged_Defective (trap case) | REFUND + PICKUP |
| 11 | C0006 | Silver · ratio 0.579 · LIKELY_ABUSER + CONFIRMED promise | REFUND + PICKUP + ABUSE_FLAG |

> **The trap case (10):** Low frustration must never downgrade a genuine high-value defect. Rule 5 (`GENUINE + Damaged_Defective → REFUND`) is placed *above* the frustration-based rules precisely to prevent this.

---

## 🚧 Key Design Decisions & Traps

The implementation plan identifies 18 named traps. The most critical:

| # | Trap | Prevention |
|---|---|---|
| 1 | **Ground-truth leakage** via `_archetype` | Drop on load: `customers.drop(columns=['_archetype'])` |
| 2 | **CONFIRMED promise to a known abuser** (C0006) | Fixed precedence: honour but cap; flag in `reason` |
| 3 | **LSTM trained on customer history** | Reader takes `messages.csv` text only; grep test enforces |
| 5 | **Treating anger as proof of genuineness** | Investigator is tone-blind; frustration never grants trust |
| 6 | **Calm high-value defect downgraded** (C0018) | Rule 5 fires before frustration rules |
| 7 | **Auto-honouring unverifiable claims** (C0004) | `UNVERIFIED` alone never triggers a payout |
| 8 | **Payouts to emotionally convincing abusers** (C0001) | Rule 3 short-circuits before value/frustration rules |
| 9 | **Over-escalation destroying automation value** | `should_escalate` fires only on two specific conditions |
| 10 | **Email firing on ACKNOWLEDGE/ESCALATE** | `email_trigger` recomputed after escalation override |
| 17 | **Inconsistent enum casing** across teammates | Single `shared/enums.py` source; no bare string literals |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/lulucare360.git
cd lulucare360
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**`requirements.txt` includes:**
```
tensorflow>=2.13
fastapi>=0.110
uvicorn[standard]
pandas
numpy
transformers
torch
scikit-learn
pytest
nbformat
jupyter
```

### 3. Train the Reader (once, offline)
```bash
cd backend
python modules/reader/train_reader.py
# Saved artifacts: backend/models/reader_issue.keras
#                  backend/models/reader_frustration.keras
#                  backend/models/tokenizer.json
#                  backend/models/label_maps.json
```

### 4. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local: set VITE_API_BASE_URL=http://localhost:8000
```

---

## 🚀 Running the System

### Development (two terminals)

**Terminal 1 — Python backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — React frontend:**
```bash
cd frontend
npm run dev
# Open http://localhost:5173
```

### Demo mode (no backend needed)
```bash
cd frontend
VITE_DEMO_MODE=true npm run dev
# Uses precomputed responses from frontend/src/demoData.js
```

### Run Module 3 notebooks (Jupyter / Google Colab)
```bash
cd lulucare360_module3
jupyter notebook
# Open enums.ipynb → economist.ipynb → test_economist.ipynb
# Run All Cells in each
```

---

## 📡 API Reference

**Base URL:** `http://localhost:8000` (dev) · `https://your-api.onrender.com` (prod)

### `POST /resolve`
Runs the full four-module pipeline.

**Request:**
```json
{
  "message": "The TV arrived with a cracked screen and won't turn on.",
  "customer_id": "C0018"
}
```

**Response** (consolidated pipeline contract):
```json
{
  "reader": {
    "issue_type": "Damaged_Defective",
    "frustration": "High",
    "confidence": 0.94
  },
  "verdict": {
    "genuineness": "GENUINE",
    "claim_status": "UNVERIFIED",
    "reason": "ratio 0.02, no abuse signals"
  },
  "decision": {
    "action": "REFUND",
    "refund_type": "PICKUP",
    "coupon_percent": 0,
    "wallet_credit": 0,
    "escalate": false,
    "email_trigger": true,
    "reason": "GENUINE + Damaged_Defective -> refund (logistics by economics)"
  },
  "reply_text": "We sincerely apologise for the damaged TV. A full refund has been processed and a courier will collect the item within 2 business days.",
  "email_subject": "Your Refund Confirmation — Order #...",
  "email_body": "Dear valued customer...",
  "audit_id": "AUD-20250623-0042"
}
```

### `GET /health`
```json
{"status": "ok", "models_loaded": true}
```

### `GET /demo/{customer_id}`
Returns a precomputed pipeline response for demo mode.

---

## 🧪 Testing

### Run all tests
```bash
cd backend
pytest -q
```

### Run Module 3 tests only
```bash
pytest tests/test_economist.py -v
```

### Expected output
```
tests/test_economist.py::test_case_01_C0005_perishable_defect_refund_keep PASSED
tests/test_economist.py::test_case_02_C0013_electronics_refund_pickup PASSED
tests/test_economist.py::test_case_03_C0001_abuser_never_pays_despite_high_value PASSED
tests/test_economist.py::test_case_04_C0004_unverified_claim_is_not_a_payout PASSED
tests/test_economist.py::test_case_05_C0034_confirmed_promise_perishable_refund_keep PASSED
tests/test_economist.py::test_case_06_C0032_economics_keep_item PASSED
tests/test_economist.py::test_case_07_C0016_first_purchase_generous_but_capped_no_escalate PASSED
tests/test_economist.py::test_case_08_C0020_low_value_genuine_low_frustration_acknowledge PASSED
tests/test_economist.py::test_case_09_C0059_escalates_no_email PASSED
tests/test_economist.py::test_case_10_C0018_calm_genuine_highvalue_defect_still_refund PASSED
tests/test_economist.py::test_case_11_C0006_abuser_with_logged_promise_honoured_but_capped PASSED
...
28 passed in 0.43s
```

### Pre-submission integration checklist
- [ ] All module tests + integration tests green (`pytest -q` → 0 failures)
- [ ] Consolidated response matches the Section 4.5 contract key-for-key
- [ ] Email fires only on `COUPON`/`REFUND`/`WALLET_CREDIT`; never on `ACKNOWLEDGE`/`ESCALATE`
- [ ] `_archetype` absent from every profile dict and every API response
- [ ] All 10 handbook test cases produce the expected resolution
- [ ] Automation rate computed and printed
- [ ] React renders all six stages from live API and from demo mode
- [ ] FLAN-T5 template fallback tested

---

## 📁 File & Folder Structure

```
lulucare360/
│
├── README.md
├── CLAUDE.md
├── .gitignore
│
├── backend/
│   ├── main.py                          # FastAPI app, /resolve + /health endpoints
│   ├── requirements.txt
│   ├── shared/
│   │   ├── enums.py                     # Single source of truth for all enum constants
│   │   └── schemas.py                   # Pydantic request/response models
│   │
│   ├── modules/
│   │   ├── reader/
│   │   │   ├── reader.py                # read_complaint(text) → reader_output
│   │   │   └── train_reader.py          # LSTM training script (run once, offline)
│   │   ├── investigator/
│   │   │   └── investigator.py          # assess_genuineness() + verify_claim()
│   │   ├── economist/
│   │   │   └── economist.py             # decide() + 4 helper functions  ← OUR MODULE
│   │   └── voice/
│   │       └── voice.py                 # generate_reply() + fire_email()
│   │
│   ├── models/                          # Trained artifacts (git-ignored if large)
│   │   ├── reader_issue.keras
│   │   ├── reader_frustration.keras
│   │   ├── tokenizer.json
│   │   └── label_maps.json
│   │
│   └── tests/
│       ├── test_reader.py
│       ├── test_investigator.py
│       ├── test_economist.py            # 28 assertions, all verified against real data
│       ├── test_voice.py
│       └── test_pipeline.py             # Integration + React contract tests
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── netlify.toml
│   ├── .env.example
│   └── src/
│       ├── App.jsx
│       ├── api_client.js
│       ├── demoData.js                  # Precomputed responses for demo mode
│       ├── shared/
│       │   └── enums.js                 # Byte-identical JS copy of shared/enums.py
│       └── components/
│           ├── MessagePanel.jsx
│           ├── ReaderPanel.jsx
│           ├── InvestigatorPanel.jsx
│           ├── EconomistPanel.jsx
│           ├── VoicePanel.jsx
│           └── EmailAuditPanel.jsx
│
├── data/
│   ├── messages.csv                     # 630 × 5 — trains the Reader
│   ├── customers.csv                    # 220 × 21 — feeds Investigator + Economist
│   └── generate_data.py                 # Synthetic data generator (seed=42)
│
├── lulucare360_module3/                 # Module 3 Jupyter notebooks
│   ├── enums.ipynb                      # Enum constants, executed
│   ├── economist.ipynb                  # All 5 functions with explanations, executed
│   └── test_economist.ipynb             # 11 cases + structural assertions, executed
│
└── docs/
    ├── architecture_diagram.png
    ├── contracts.md                     # Frozen interface contracts
    └── trust_memo.md                    # VP Reem memo
```

---

## 🌐 Deployment

### Frontend → Netlify

```toml
# netlify.toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

Set environment variable in Netlify dashboard:
```
VITE_API_BASE_URL = https://your-api.onrender.com
```

### Backend → Render / Railway / Hugging Face Spaces

**Render:**
1. Connect GitHub repo → New Web Service
2. Build command: `pip install -r backend/requirements.txt`
3. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Set `ALLOWED_ORIGINS = https://your-app.netlify.app`

**CORS config in `main.py`:**
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGINS"), "http://localhost:5173"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
```

---

## 📈 Automation Rate & Trust Memo Highlights

```
Automation Rate = (cases where action ≠ ESCALATE) / total cases
Target: ≥ 90% on the 10 handbook test cases
```

Over the 10 test cases, only **Case 9** (C0059: SUSPICIOUS + HIGH value + low confidence) is designed to escalate, giving a correct system an automation rate of **~90%**.

**The three-way balance the system must navigate:**

| Goal | Risk if over-tuned |
|---|---|
| 🛡 Protect revenue (don't over-pay abusers) | Genuine customers wrongly denied |
| 💎 Protect retention (don't under-serve genuine high-value customers) | Revenue loss, churn |
| ⏱ Protect team time (don't over-escalate) | Automation business case collapses |

**Trust memo headline:** LuluCare 360 recommends human review for: (1) any `ESCALATE` case, (2) any `CONFIRMED` promise to a `LIKELY_ABUSER`, and (3) any case where `confidence < 0.5`. Fully autonomous action is appropriate for the remaining ~90% of cases.

---

## 👥 Team & Contributions

| Member | Roll No | Module | Responsibility |
|---|---|---|---|
| Krishna Mathur | AS25DXB018 | **Module 3 — Economist** | `economist.py`, all 5 functions, 11 test cases, notebooks |
| *(teammate)* | | Module 1 — Reader | LSTM training, RNN comparison, frustration classifier |
| *(teammate)* | | Module 2 — Investigator | Trust rules, claim verification |
| *(teammate)* | | Module 4 — Voice | FLAN-T5, email trigger, React dashboard, integration |

**Institution:** SP Jain School of Global Management, Dubai Campus  
**Programme:** Master of AI in Business (MAIB)  
**Course:** Natural Language Processing & NLG/Dialogue Systems  
**Batch:** September 2025 · Term 3 · Roll No: AS25DXB018

---

## 📚 References

### Core NLP & Deep Learning

1. **Hochreiter, S. & Schmidhuber, J. (1997).** Long Short-Term Memory. *Neural Computation, 9*(8), 1735–1780. https://doi.org/10.1162/neco.1997.9.8.1735
   > *Foundational paper for the LSTM architecture used in the Reader module.*

2. **Goodfellow, I., Bengio, Y., & Courville, A. (2016).** *Deep Learning.* MIT Press. https://www.deeplearningbook.org
   > *Chapters 10 (Sequence Modelling) and 6 (Feedforward Networks) inform the Reader architecture.*

3. **Mikolov, T., Chen, K., Corrado, G., & Dean, J. (2013).** Efficient Estimation of Word Representations in Vector Space. *arXiv:1301.3781*. https://arxiv.org/abs/1301.3781
   > *Word2Vec embeddings — conceptual basis for the Embedding layer in the Reader.*

4. **Cho, K., et al. (2014).** Learning Phrase Representations using RNN Encoder–Decoder for Statistical Machine Translation. *arXiv:1406.1078*. https://arxiv.org/abs/1406.1078
   > *GRU/RNN encoder-decoder work — background for the SimpleRNN vs LSTM experiment.*

### Pre-trained Models & NLG

5. **Raffel, C., et al. (2020).** Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer (T5). *Journal of Machine Learning Research, 21*(140), 1–67. https://jmlr.org/papers/v21/20-074.html
   > *The T5 paper — basis for FLAN-T5 used in the Voice module.*

6. **Wei, J., et al. (2022).** Finetuned Language Models Are Zero-Shot Learners (FLAN). *ICLR 2022*. https://arxiv.org/abs/2109.01652
   > *FLAN instruction-tuning — explains why `google/flan-t5-small` follows task instructions without fine-tuning.*

7. **Hugging Face Transformers Documentation.** https://huggingface.co/docs/transformers
   > *Library used to load and run FLAN-T5 in the Voice module.*

### Dialogue Systems & Dialogue Policy

8. **Young, S., et al. (2013).** POMDP-Based Statistical Spoken Dialogue Systems: A Review. *Proceedings of the IEEE, 101*(5), 1160–1179. https://doi.org/10.1109/JPROC.2012.2225812
   > *Dialogue policy theory — the Investigator + Economist together constitute the dialogue policy layer.*

9. **Williams, J. D., & Young, S. (2007).** Partially Observable Markov Decision Processes for Spoken Dialog Systems. *Computer Speech & Language, 21*(2), 393–422.
   > *Background on state-tracking and action-selection in dialogue, applied conceptually to the pipeline.*

10. **Jurafsky, D., & Martin, J. H. (2024).** *Speech and Language Processing* (3rd ed. draft). https://web.stanford.edu/~jurafsky/slp3/
    > *Chapters on RNNs, LSTMs (Ch. 9), dialogue systems (Ch. 24), and NLG (Ch. 23).*

### Frameworks & Libraries

11. **TensorFlow/Keras Documentation.** https://www.tensorflow.org/api_docs/python/tf/keras
    > *LSTM, Embedding, Dense layers used in the Reader.*

12. **FastAPI Documentation.** https://fastapi.tiangolo.com
    > *Backend REST API framework.*

13. **React Documentation.** https://react.dev
    > *Frontend framework for the six-stage dashboard.*

14. **Pandas Documentation.** https://pandas.pydata.org/docs
    > *Data loading, profiling, and the `_archetype` drop-on-load pattern.*

15. **Netlify Documentation.** https://docs.netlify.com
    > *Static hosting, SPA redirect configuration, environment variables.*

### Business Context & AI Ethics

16. **Brynjolfsson, E., & McAfee, A. (2014).** *The Second Machine Age.* W.W. Norton.
    > *Automation economics and the human-in-the-loop trade-off in customer service AI.*

17. **Doshi-Velez, F., & Kim, B. (2017).** Towards a Rigorous Science of Interpretable Machine Learning. *arXiv:1702.08608*. https://arxiv.org/abs/1702.08608
    > *Motivation for using transparent rule engines (Investigator, Economist) rather than black-box models for trust and money decisions.*

18. **Russell, S., & Norvig, P. (2020).** *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson.
    > *Chapter 22 (NLP) and Chapter 16 (Decision-making under uncertainty) — conceptual grounding.*

---

<div align="center">

**Built with 🧠 for MAIB · NLP & NLG/Dialogue Systems · SP Jain Dubai**

*LuluCare 360 is an academic project. All customer data is synthetic. No real Lulu customer data was used.*

</div>

# CLAUDE.md — LuluCare 360
> This file is the AI context brief for Claude (or any AI assistant) working on this codebase.
> Read it completely before writing, editing, or reviewing any file in this repo.

---

## 1. What This Project Is

**LuluCare 360** is a four-module AI complaint-resolution pipeline for Lulu Hypermarket.  
A customer complaint message and a `customer_id` go in. A structured resolution decision, a natural-language reply, and a conditional email come out.

**Academic context:** MAIB · NLP & NLG/Dialogue Systems · SP Jain School of Global Management, Dubai  
**Batch:** September 2025 · Term 3 · Roll No (Module 3 owner): AS25DXB018

The pipeline has a strict one-direction data flow:

```
[Message + customer_id]
        ↓
  Module 1: Reader      (LSTM)                  → issue_type, frustration, confidence
        ↓
  Module 2: Investigator (rules)                → genuineness, claim_status
        ↓
  Module 3: Economist   (rules) ← OUR MODULE   → action, refund_type, email_trigger, ...
        ↓
  Module 4: Voice       (FLAN-T5)               → reply_text, email_body
        ↓
  [Consolidated response → React dashboard]
```

---

## 2. Absolute Non-Negotiables (NEVER Violate)

These are hard rules. Breaking any one of them will fail a test or break integration silently.

### 2.1 Contract Keys Are Frozen
The output dictionaries from each module have **immutable keys**. Do not rename, add, or remove any key from:
- `reader_output` → `{issue_type, frustration, confidence}`
- `verdict` → `{genuineness, claim_status, reason}`
- `decision` → `{action, refund_type, coupon_percent, wallet_credit, escalate, email_trigger, reason}`
- Consolidated response → `{reader, verdict, decision, reply_text, email_subject, email_body, audit_id}`

### 2.2 All Return Values Must Be Native Python Types
pandas profiles return NumPy scalars (`np.int64`, `np.bool_`, etc.). These silently break JSON serialization and crash the React layer. Cast **every** value before returning:
```python
# WRONG:
return {"escalate": np.bool_(True)}      # np.bool_ will break JSON

# RIGHT:
return {"escalate": bool(escalate)}      # native Python bool
```
The test `test_all_returned_values_are_native_python_types` will catch any leakage.

### 2.3 Never Use Bare String Literals in Branch Logic
All allowed string values live in `shared/enums.py`. Import the constants; never retype them.
```python
# WRONG:
if verdict["genuineness"] == "Likely_Abuser":   # wrong case; silent fail

# RIGHT:
from shared.enums import LIKELY_ABUSER
if verdict["genuineness"] == LIKELY_ABUSER:
```

### 2.4 Never Read `_archetype`
`customers.csv` contains a column `_archetype` (the ground-truth label). It is a leakage trap. It must be:
- Dropped at load: `customers.drop(columns=['_archetype'], errors='ignore')`
- Used **only** inside test files to score the Investigator
- Never present in any profile dict passed between modules
- Never present in any API response

### 2.5 The Economist Is Text-Free
`economist.py` must never return a customer-facing sentence. The `reason` field is an **internal** explanation only — it goes to the logs and the internal dashboard panel, never directly to the customer. The Voice module writes the reply.

### 2.6 The Investigator Is Tone-Blind
`assess_genuineness()` must never read `reader_output["frustration"]` or the raw message text. Trust is computed from account history records only. Frustration cannot raise trust or release money.

### 2.7 The Reader Is History-Blind
`read_complaint()` takes only the raw text. It must never import from `customers.csv` or receive any history fields. A grep test (`test_reader.py`) enforces this.

### 2.8 `email_trigger` Is Set Once, by the Economist, After Escalation
```python
# Correct orchestration order in decide():
escalate = should_escalate(...)
if escalate: action = ACTION_ESCALATE
email_trigger = action in EMAIL_ACTIONS  # recomputed AFTER the override
```
- `ACKNOWLEDGE` → **never** emails
- `ESCALATE` → **never** emails  
- `COUPON` / `REFUND` / `WALLET_CREDIT` → **always** emails

The Voice must **obey** `email_trigger`; it must never recompute it.

---

## 3. Module 3 — The Economist: Complete Function Reference

**File:** `backend/modules/economist/economist.py`

### Enum Constants (import, never retype)
```python
from shared.enums import (
    GENUINE, SUSPICIOUS, LIKELY_ABUSER,           # genuineness
    CONFIRMED, CONTRADICTED, UNVERIFIED,           # claim_status
    ACTION_ACKNOWLEDGE, ACTION_COUPON,             # actions
    ACTION_WALLET_CREDIT, ACTION_REFUND,
    ACTION_ESCALATE, ACTIONS, EMAIL_ACTIONS,
    REFUND_PICKUP, REFUND_KEEP_ITEM, REFUND_NONE,  # logistics
    REFUND_TYPES, FRUST_LOW, FRUST_MEDIUM,
    FRUST_HIGH, TIER_GOLD, TIER_SILVER,
    TIER_PLATINUM, ISSUE_DAMAGED_DEFECTIVE,
    VALUE_HIGH, VALUE_MEDIUM, VALUE_LOW,
)
```

### Tunable Policy Knobs (all in one place at top of file)
```python
COUPON_STANDARD          = 20      # % — default goodwill coupon
COUPON_GENEROUS          = 50      # % — high-frustration + HIGH-value
WALLET_CREDIT_BY_BAND    = {VALUE_LOW: 50, VALUE_MEDIUM: 100, VALUE_HIGH: 200}  # AED
NEW_ACCOUNT_MAX_MONTHS   = 2       # "newbie" threshold
HIGH_RESALE_THRESHOLD    = 2000    # AED — above this, electronics always retrieved
ESCALATE_ORDER_VALUE     = 5000    # AED — large-money escalation threshold
LOW_CONFIDENCE           = 0.5     # Reader confidence floor for escalation
```

### `value_band(p: dict) → str`
```
Platinum OR clv ≥ 40000   →  VALUE_HIGH
Gold/Silver OR clv ≥ 12000 →  VALUE_MEDIUM
else                       →  VALUE_LOW
```
**Profile fields used:** `loyalty_tier`, `clv_estimate`  
**Never used to grant trust — only to scale remediation within an already-trusted path.**

### `refund_logistics(p: dict) → str`
*(Only called when `action == ACTION_REFUND`)*
```
is_perishable_or_hygiene True        →  REFUND_KEEP_ITEM  (cannot resell)
resale_value >= 2000                 →  REFUND_PICKUP     (costly; always recover)
reverse_logistics_cost > resale_value →  REFUND_KEEP_ITEM  (freight costs more)
else                                 →  REFUND_PICKUP
```
**Profile fields used:** `is_perishable_or_hygiene`, `resale_value`, `reverse_logistics_cost`

### `should_escalate(verdict, reader, p, proposed_refund) → bool`
Fires **only** on these two conditions:
1. `proposed_refund AND verdict["genuineness"] == SUSPICIOUS AND p["order_value"] > 5000`
2. `reader["confidence"] < 0.5 AND value_band(p) == VALUE_HIGH`

**Use sparingly.** Over-escalation destroys the automation business case.

### `choose_action(verdict, reader, p) → (action, coupon_percent, wallet_credit, reason_note)`
**8-rule tier table. Evaluate top-to-bottom. First match wins. ORDER IS THE ANTI-ABUSE PRECEDENCE.**

| # | Condition | Action | coupon_% | wallet |
|---|---|---|---|---|
| 1 | `claim_status == CONTRADICTED` | ACKNOWLEDGE | 0 | 0 |
| 2 | `claim_status == CONFIRMED` | REFUND (or COUPON if notes say so) | per notes | 0 |
| 2b | `CONFIRMED + LIKELY_ABUSER` | Same as above but ABUSE_FLAG in reason | per notes | 0 |
| 3 | `genuineness == LIKELY_ABUSER` | ACKNOWLEDGE | 0 | 0 |
| 4 | `is_first_purchase OR age_months ≤ 2` | COUPON | 20 | 0 |
| 5 | `GENUINE + Damaged_Defective` | REFUND | 0 | 0 |
| 6 | `GENUINE + High + VALUE_HIGH` | COUPON | 50 | 0 |
| 7 | `GENUINE + Medium + VALUE_LOW` | WALLET_CREDIT | 0 | 50 |
| 7b | `GENUINE + Medium + (MED or HIGH)` | COUPON | 20 | 0 |
| 8 | Everything else | ACKNOWLEDGE | 0 | 0 |

> **Rule 5 is placed above Rules 6–8 on purpose.** A calm, genuine, high-value defect (C0018: Platinum, Low frustration, Damaged_Defective) must still get a full REFUND. Low frustration must never downgrade a genuine defect.

### `decide(verdict, reader, p) → dict`
The only public function. Orchestration order is fixed:
```python
def decide(verdict, reader, p):
    action, coupon_percent, wallet_credit, note = choose_action(verdict, reader, p)
    refund_type   = refund_logistics(p) if action == ACTION_REFUND else REFUND_NONE
    escalate      = should_escalate(verdict, reader, p, proposed_refund=(action==ACTION_REFUND))
    if escalate:
        action = ACTION_ESCALATE
        note   = note + " | OVERRIDE: escalated to human (high stakes + low certainty)"
    email_trigger = action in EMAIL_ACTIONS   # AFTER escalation
    return {
        "action":         str(action),
        "refund_type":    str(refund_type),
        "coupon_percent": int(coupon_percent),
        "wallet_credit":  int(wallet_credit),
        "escalate":       bool(escalate),
        "email_trigger":  bool(email_trigger),
        "reason":         str(note),
    }
```

---

## 4. Shared Enums — Casing Reference

All string values crossing a module boundary must use this **exact** casing.

| Category | Values | Casing |
|---|---|---|
| `genuineness` | `GENUINE`, `SUSPICIOUS`, `LIKELY_ABUSER` | `UPPER_SNAKE` |
| `claim_status` | `CONFIRMED`, `CONTRADICTED`, `UNVERIFIED` | `UPPER_SNAKE` |
| `action` | `ACKNOWLEDGE`, `COUPON`, `WALLET_CREDIT`, `REFUND`, `ESCALATE` | `UPPER_SNAKE` |
| `refund_type` | `PICKUP`, `KEEP_ITEM`, `NONE` | `UPPER_SNAKE` |
| `issue_type` | `Delivery`, `Damaged_Defective`, `Refund_Return`, `Billing`, `Product_Quality`, `App_Technical`, `General_Query` | `TitleCase` |
| `loyalty_tier` | `Bronze`, `Silver`, `Gold`, `Platinum` | `TitleCase` |
| `frustration` | `Low`, `Medium`, `High` | `First-letter capital` |
| value bands (internal) | `HIGH`, `MEDIUM`, `LOW` | `UPPER` |

---

## 5. Dataset Facts (Verified)

Always reference these numbers; do not re-derive or guess.

### `messages.csv` (630 × 5)
- Exactly **90 messages per issue type** (7 types)
- Exactly **210 messages per frustration level** (3 levels)
- Exactly **30 messages** in every `issue_type × frustration` cell — no oversampling needed
- Mean message length: **14 words**, max: **23 words** → `MAXLEN = 40` truncates nothing
- 205 distinct customers referenced (out of 220)

### `customers.csv` (220 × 21)
- **120 GENUINE · 55 SUSPICIOUS · 45 LIKELY_ABUSER**
- Loyalty: Bronze 68 · Silver 70 · Gold 54 · Platinum 28
- Value bands: HIGH 84 · MEDIUM 111 · LOW 25
- 110 perishable/hygiene customers → all resolve to `KEEP_ITEM` in logistics
- Refund logistics split: **114 KEEP_ITEM · 106 PICKUP**
- 33 customers with `prior_promise_logged = True` → all `CONFIRMED`
- All 220 customers have non-empty `customer_care_notes`
- Average `order_value`: AED 7,958 · Average `clv_estimate`: AED 48,066
- **`_archetype` is a leakage trap — drop on load, use only in test scoring**

---

## 6. The 11 Verified Test Cases (Module 3)

These are pinned to real `customers.csv` rows. Do not change the expected outputs.

| # | `customer_id` | Key profile facts | Mock verdict | Expected `action` | Expected `refund_type` | `email_trigger` |
|---|---|---|---|---|---|---|
| 1 | C0005 | Gold · perishable · clv 37040 | GENUINE / UNVERIFIED | REFUND | KEEP_ITEM | True |
| 2 | C0013 | Silver · Electronics resale 34890 | GENUINE / UNVERIFIED | REFUND | PICKUP | True |
| 3 | C0001 | Silver · ratio 0.833 · clv 159720 | LIKELY_ABUSER / UNVERIFIED | ACKNOWLEDGE | NONE | False |
| 4 | C0004 | Silver · no promise logged | GENUINE / UNVERIFIED | ACKNOWLEDGE | NONE | False |
| 5 | C0034 | Bronze · perishable · promise logged | GENUINE / CONFIRMED | REFUND | KEEP_ITEM | True |
| 6 | C0032 | Silver · Fashion · resale 164 < freight 180 | GENUINE / UNVERIFIED | REFUND | KEEP_ITEM | True |
| 7 | C0016 | Gold · first purchase · age 0 months | SUSPICIOUS / UNVERIFIED | COUPON | NONE | True |
| 8 | C0020 | Bronze · clv 4959 · LOW value | GENUINE / UNVERIFIED | ACKNOWLEDGE | NONE | False |
| 9 | C0059 | Platinum · order 24392 · conf 0.45 | SUSPICIOUS / UNVERIFIED | ESCALATE | NONE | False |
| 10 | C0018 | Platinum · clv 117030 · **Low frustration** (trap) | GENUINE / UNVERIFIED | REFUND | PICKUP | True |
| 11 | C0006 | Silver · ratio 0.579 · promise logged | LIKELY_ABUSER / CONFIRMED | REFUND | PICKUP | True |

**⚠️ Boundary flag (Case 9):** C0059 has `refund_to_order_ratio = 0.5` exactly. The Investigator's own rule (`ratio ≥ 0.5 → LIKELY_ABUSER`) would label it `LIKELY_ABUSER`. The test deliberately mocks verdict as `SUSPICIOUS` to exercise the escalation valve. The Module 2 owner must be informed of this boundary case.

---

## 7. Integration Rules (Summary)

Full list is in `docs/contracts.md`. The top-priority rules for AI coding:

1. **No key renaming** — caught by schema tests in `test_pipeline.py`
2. **Everything JSON-safe** — cast with `int()`, `float()`, `bool()`, `str()` before returning
3. **One enum source** — `shared/enums.py` only; no bare string literals in branch logic
4. **`_archetype` quarantined** — drop at load, test-only, never in a response
5. **Reader isolation** — `reader.py` never imports from `customers.csv`
6. **Investigator tone-blindness** — `assess_genuineness()` never reads `frustration`
7. **Economist text-free** — `decide()` never returns a customer sentence
8. **Voice decision-preserving** — `generate_reply()` never changes `action`, amounts, or `email_trigger`
9. **Email rule centralized** — set once in Economist, obeyed by Voice, never recomputed

---

## 8. Common Mistakes to Avoid

These are real failure modes identified in the implementation plan traps audit:

```python
# ❌ WRONG: returning NumPy types
return {"escalate": np.bool_(True), "coupon_percent": np.int64(20)}

# ✅ RIGHT: native Python only
return {"escalate": bool(True), "coupon_percent": int(20)}

# ❌ WRONG: recomputing email_trigger before escalation
email_trigger = action in EMAIL_ACTIONS   # too early
if escalate: action = ACTION_ESCALATE     # now email_trigger is wrong

# ✅ RIGHT: escalation first, then email
if escalate: action = ACTION_ESCALATE
email_trigger = action in EMAIL_ACTIONS   # correct: after override

# ❌ WRONG: bare string literals
if verdict["genuineness"] == "LIKELY_ABUSER":   # typo risk

# ✅ RIGHT: enum constants
if verdict["genuineness"] == LIKELY_ABUSER:

# ❌ WRONG: frustration granting a payout without trust check
if reader["frustration"] == "High":
    return ACTION_REFUND   # abuser writes the angriest message of all

# ✅ RIGHT: trust check before any generosity
if genuineness == LIKELY_ABUSER:
    return ACTION_ACKNOWLEDGE   # Rule 3 fires before frustration rules

# ❌ WRONG: reading _archetype
archetype = profile["_archetype"]   # leakage trap

# ✅ RIGHT: _archetype dropped on load, never in profile
customers = pd.read_csv("customers.csv").drop(columns=["_archetype"], errors="ignore")
```

---

## 9. How to Run Tests

```bash
# All tests
cd backend && pytest -q

# Module 3 only (verbose)
pytest tests/test_economist.py -v

# Structural assertions only
pytest tests/test_economist.py -k "structural" -v

# In Jupyter (no pytest needed)
# Open test_economist.ipynb → Kernel → Restart & Run All
# Every cell prints PASS ✅ or raises AssertionError with a clear message
```

**Expected:** 28 assertions, all green, in ~0.4 seconds.

---

## 10. How to Run the Full Pipeline

```bash
# Terminal 1: Python backend
cd backend && source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: React frontend
cd frontend && npm run dev

# Quick smoke test via curl
curl -X POST http://localhost:8000/resolve \
  -H "Content-Type: application/json" \
  -d '{"message": "My TV arrived with a cracked screen", "customer_id": "C0018"}'
```

---

## 11. Files Claude Should Never Modify Without Explicit Permission

| File | Reason |
|---|---|
| `shared/enums.py` | Contract source of truth — any change needs all 4 module owners to agree |
| `shared/schemas.py` | API contract — change breaks React |
| `docs/contracts.md` | Frozen interface spec |
| `data/messages.csv` | Training data |
| `data/customers.csv` | Customer data |
| `backend/models/*.keras` | Trained model weights |

---

## 12. Glossary

| Term | Definition |
|---|---|
| **Reader** | Module 1; LSTM that classifies `issue_type` and `frustration` from raw text |
| **Investigator** | Module 2; rule engine that outputs `genuineness` and `claim_status` from account history |
| **Economist** | Module 3; rule engine that outputs the `decision` (action, refund, email) |
| **Voice** | Module 4; FLAN-T5 that writes the reply and triggers the email |
| **value_band** | Internal Economist classification: HIGH / MEDIUM / LOW based on CLV + tier |
| **refund_logistics** | Whether to send a courier (PICKUP) or let customer keep the item (KEEP_ITEM) |
| **escalate** | Hand the case to a human agent; overrides all proposed actions |
| **email_trigger** | Bool; fires email for COUPON/REFUND/WALLET_CREDIT; never for ACKNOWLEDGE/ESCALATE |
| **_archetype** | Ground-truth label in `customers.csv`; leakage trap; drop on load |
| **CONFIRMED** | Our agent notes corroborate the customer's claim of a prior promise |
| **CONTRADICTED** | Our agent notes actively disprove the customer's claim |
| **UNVERIFIED** | No prior contact record; claim cannot be confirmed or denied |
| **automation_rate** | % of cases resolved without human escalation; target ≥ 90% |
| **CLV** | Customer Lifetime Value estimate (annualised) in AED |
| **NLU** | Natural Language Understanding — the Reader maps text → structured meaning |
| **NLG** | Natural Language Generation — the Voice maps structured decision → text |
| **dialogue policy** | The decision-making layer between NLU and NLG; the Investigator + Economist together |

---

*This file is part of the LuluCare 360 repository — MAIB · SP Jain Dubai · September 2025 Batch.*

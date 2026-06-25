# Module 3 — The Economist — Steering Context
> **2-minute brief for teammates building Modules 1, 2, and 4.**  
> Read this instead of the full notebook. It tells you exactly what Module 3 does, what it needs from you, and what it hands back.

---

## What Module 3 Is (One Paragraph)

The Economist is a **pure-economics rule engine** — no model, no randomness, no learning. It sits between the Investigator (trust verdict) and the Voice (reply writer). It receives three inputs: the Investigator's trust verdict, the Reader's issue/frustration output, and the customer's profile from `customers.csv`. It fuses them into a single structured **decision dictionary** that tells the Voice what action to take and whether to fire an email. It never writes a customer-facing sentence. It never changes trust. It never reads `_archetype`.

---

## The One Function You Call

```python
from backend.modules.economist.economist import decide

decision = decide(verdict, reader_output, profile)
```

That's it. One function in, one dict out. Mock the inputs and you can test Module 3 completely independently of everyone else.

---

## What You Must Give It (Inputs)

### From Module 2 — The Investigator
```python
verdict = {
    "genuineness":  "GENUINE" | "SUSPICIOUS" | "LIKELY_ABUSER",
    "claim_status": "CONFIRMED" | "CONTRADICTED" | "UNVERIFIED",
    "reason":       str   # your internal explanation — Economist reads it for CONFIRMED promise type
}
```

### From Module 1 — The Reader
```python
reader_output = {
    "issue_type":  str,    # one of the 7 TitleCase types (see enums.py)
    "frustration": str,    # "Low" | "Medium" | "High"   ← exact casing
    "confidence":  float   # [0.0, 1.0] — used by the escalation valve
}
```

### From the profile loader (shared utility)
```python
profile = lookup_profile(customer_id)
# Returns a customers.csv row as a dict with _archetype already dropped.
# Economist reads: loyalty_tier, clv_estimate, order_value, is_first_purchase,
#                  account_age_months, is_perishable_or_hygiene,
#                  resale_value, reverse_logistics_cost
```

---

## What You Get Back (Output Contract — FROZEN)

```python
decision = {
    "action":         str,   # "ACKNOWLEDGE"|"COUPON"|"WALLET_CREDIT"|"REFUND"|"ESCALATE"
    "refund_type":    str,   # "PICKUP" | "KEEP_ITEM" | "NONE"
    "coupon_percent": int,   # 0 | 20 | 50   (no other values ever)
    "wallet_credit":  int,   # AED, 0 if not applicable
    "escalate":       bool,  # True → hand to human agent
    "email_trigger":  bool,  # True iff action in {COUPON, REFUND, WALLET_CREDIT}
    "reason":         str    # internal log note — NOT a customer sentence
}
```

**Every value is a native Python type** (`str`, `int`, `bool`) — never NumPy. Safe to `json.dumps()` directly.

---

## The Decision Logic (What Happens Inside)

The Economist runs **4 functions** in a fixed order. You don't call them — `decide()` does. Shown here so you understand the output you receive.

### Step 1 — `value_band(profile)` → `"HIGH"` / `"MEDIUM"` / `"LOW"`
```
Platinum OR clv ≥ 40,000   →  HIGH
Gold/Silver OR clv ≥ 12,000 →  MEDIUM
else                        →  LOW
```
Value **never grants trust** — it only scales the size of a remedy within an already-trusted path.

### Step 2 — `choose_action()` — 8-Rule Tier Table
Evaluated **top to bottom, first match wins.** This order is the anti-abuse precedence — do not reorder.

| # | Condition | Action | Coupon |
|---|---|---|---|
| 1 | `claim_status == CONTRADICTED` | ACKNOWLEDGE | 0% |
| 2 | `claim_status == CONFIRMED` | REFUND (or COUPON if notes say %) | per notes |
| 3 | `genuineness == LIKELY_ABUSER` | ACKNOWLEDGE | 0% |
| 4 | First purchase OR `account_age_months ≤ 2` | COUPON | 20% |
| 5 | `GENUINE` + `Damaged_Defective` | REFUND | — |
| 6 | `GENUINE` + `High` frustration + `HIGH` value | COUPON | 50% |
| 7 | `GENUINE` + `Medium` frustration | COUPON / WALLET_CREDIT | 20% / AED 50–200 |
| 8 | Everything else | ACKNOWLEDGE | 0% |

> **Rule 5 is above Rule 6 on purpose.** A Platinum customer who complains calmly about a broken item still gets a full REFUND — Low frustration must never downgrade a genuine defect.

### Step 3 — `refund_logistics(profile)` → `"PICKUP"` / `"KEEP_ITEM"` / `"NONE"`
Only runs if `action == REFUND`.
```
is_perishable_or_hygiene           →  KEEP_ITEM  (can't resell; don't waste freight)
resale_value ≥ AED 2,000           →  PICKUP     (electronics/appliances; recover it)
reverse_logistics_cost > resale    →  KEEP_ITEM  (shipping costs more than it's worth)
else                               →  PICKUP
```

### Step 4 — `should_escalate()` → `bool`
Fires on **exactly two conditions**:
1. Proposed `REFUND` + `SUSPICIOUS` trust + `order_value > AED 5,000`
2. Reader `confidence < 0.5` + value band = `HIGH`

If it fires → `action` becomes `ESCALATE` and `email_trigger` becomes `False`.

---

## Three Things Module 3 Will NEVER Do

| Never | Why |
|---|---|
| Return a customer-facing sentence | That is the Voice's job. `reason` is an internal note. |
| Use `frustration` to grant trust or release money on its own | Anger is not evidence. An abuser writes the most furious message of all. |
| Read `_archetype` from the profile | Leakage trap. It is dropped before the profile reaches Module 3. |

---

## What This Means for Each Other Module

### 👉 If you are building Module 1 (The Reader)
- You must output **exactly** `{"issue_type", "frustration", "confidence"}` — no extra keys, no missing keys.
- Casing matters: `"Damaged_Defective"` not `"damaged_defective"`, `"High"` not `"HIGH"`.
- `confidence` must be a native Python `float` in `[0.0, 1.0]`. The escalation valve uses it.
- Low confidence on a HIGH-value customer will trigger escalation — so test ambiguous messages.

### 👉 If you are building Module 2 (The Investigator)
- You must output **exactly** `{"genuineness", "claim_status", "reason"}`.
- `reason` is more than a label — for `CONFIRMED` cases the Economist scans it for the word `"coupon"` or a `%` symbol to decide whether to honour a coupon or a refund. Write it descriptively: e.g. `"Agent promised 20% coupon on previous call, not yet issued."`
- **Boundary flag (C0059):** `refund_to_order_ratio` is exactly `0.5` for this customer. Your threshold `ratio ≥ 0.5 → LIKELY_ABUSER` would label them `LIKELY_ABUSER`. However, Module 3 test case 9 mocks them as `SUSPICIOUS` to exercise the escalation valve. Agree on which verdict to emit for `ratio == 0.5` exactly — and be consistent.

### 👉 If you are building Module 4 (The Voice)
- You receive the full `decision` dict above. Read it verbatim — do not rename keys.
- **Obey `email_trigger`** — do not recompute it. The Economist sets it after the escalation override; recomputing it in the Voice can cause emails to fire on `ESCALATE` cases.
- `action == "ACKNOWLEDGE"` → courteous reply, promise nothing, no email.
- `action == "ESCALATE"` → inform customer a specialist will follow up, no email.
- `action == "REFUND"` → check `refund_type`: if `KEEP_ITEM`, tell them to keep/dispose; if `PICKUP`, tell them a courier will collect.
- `reason` is for the internal dashboard panel only — never paste it into the customer reply.

---

## Mock Inputs for Testing Your Module Against Module 3

Copy-paste these into your test file. They cover every action the Economist can return.

```python
from backend.shared.enums import *

# Returns REFUND + KEEP_ITEM + email_trigger True
v1 = {"genuineness": GENUINE, "claim_status": UNVERIFIED, "reason": ""}
r1 = {"issue_type": "Damaged_Defective", "frustration": "High", "confidence": 0.91}
p1 = {"loyalty_tier": "Gold", "clv_estimate": 37040, "order_value": 394,
      "is_first_purchase": False, "account_age_months": 27,
      "is_perishable_or_hygiene": True, "resale_value": 0, "reverse_logistics_cost": 108}

# Returns ACKNOWLEDGE + email_trigger False (abuser, no payout)
v2 = {"genuineness": LIKELY_ABUSER, "claim_status": UNVERIFIED, "reason": "ratio 0.833"}
r2 = {"issue_type": "Delivery", "frustration": "High", "confidence": 0.90}
p2 = {"loyalty_tier": "Silver", "clv_estimate": 159720, "order_value": 9164,
      "is_first_purchase": False, "account_age_months": 1,
      "is_perishable_or_hygiene": False, "resale_value": 5956, "reverse_logistics_cost": 101}

# Returns COUPON 20% + email_trigger True (first purchase)
v3 = {"genuineness": SUSPICIOUS, "claim_status": UNVERIFIED, "reason": ""}
r3 = {"issue_type": "Delivery", "frustration": "High", "confidence": 0.85}
p3 = {"loyalty_tier": "Gold", "clv_estimate": 16176, "order_value": 2293,
      "is_first_purchase": True, "account_age_months": 0,
      "is_perishable_or_hygiene": False, "resale_value": 917, "reverse_logistics_cost": 253}

# Returns ESCALATE + email_trigger False (low confidence + HIGH value)
v4 = {"genuineness": SUSPICIOUS, "claim_status": UNVERIFIED, "reason": ""}
r4 = {"issue_type": "Damaged_Defective", "frustration": "High", "confidence": 0.45}
p4 = {"loyalty_tier": "Platinum", "clv_estimate": 114588, "order_value": 24392,
      "is_first_purchase": False, "account_age_months": 1,
      "is_perishable_or_hygiene": False, "resale_value": 14635, "reverse_logistics_cost": 212}

# Returns WALLET_CREDIT AED 50 + email_trigger True (GENUINE + Medium + LOW value)
v5 = {"genuineness": GENUINE, "claim_status": UNVERIFIED, "reason": ""}
r5 = {"issue_type": "Billing", "frustration": "Medium", "confidence": 0.88}
p5 = {"loyalty_tier": "Bronze", "clv_estimate": 4959, "order_value": 224,
      "is_first_purchase": False, "account_age_months": 61,
      "is_perishable_or_hygiene": True, "resale_value": 0, "reverse_logistics_cost": 118}
```

---

## File Map (Module 3 only)

```
backend/
└── modules/
    └── economist/
        └── economist.py          ← the only file you need to call

backend/tests/
└── test_economist.py             ← 28 assertions, all green

backend/shared/
└── enums.py                      ← import constants from here, never retype them

lulucare360_module3/
├── enums.ipynb                   ← all enum constants, explained and executed
├── economist.ipynb               ← all 5 functions, explained and executed
└── test_economist.ipynb          ← 11 test cases + structural assertions, executed
```

---

## Email Truth Table (quick reference)

| `action` | `email_trigger` | `escalate` |
|---|---|---|
| `ACKNOWLEDGE` | `False` | `False` |
| `COUPON` | `True` | `False` |
| `WALLET_CREDIT` | `True` | `False` |
| `REFUND` | `True` | `False` |
| `ESCALATE` | `False` | `True` |

---

*Module 3 owner: Krishna Mathur · AS25DXB018 · SP Jain MAIB Dubai · September 2025 Batch*

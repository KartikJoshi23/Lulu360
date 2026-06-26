# Interface Contracts (frozen)

Human-readable copy of Implementation Plan §4. These dictionaries are the
boundaries the four modules pass to each other. **Keys are immutable** — renaming
one is a contract breach caught by the schema tests. The Python source of truth
is `shared/schemas.py`; enum string values are fixed in `shared/enums.py`
(mirrored byte-for-byte in `shared/enums.js`).

> All values are JSON-safe native Python types (`str`/`int`/`float`/`bool`). No
> NumPy scalars cross a boundary (cast with `int()`/`float()`/`bool()`/`str()`).

---

## 1. Reader output — `read_message(text) -> dict`
```jsonc
{
  "issue_type":  "Delivery",   // one of 7 TitleCase types (see enums.ISSUE_TYPES)
  "frustration": "High",       // Low | Medium | High
  "confidence":  0.87          // float [0,1] — issue softmax max
}
```

## 2. Investigator output — `investigate(reader_output, profile, conversation_history=None) -> dict`
```jsonc
{
  "genuineness":  "GENUINE",      // GENUINE | SUSPICIOUS | LIKELY_ABUSER
  "claim_status": "UNVERIFIED",   // CONFIRMED | CONTRADICTED | UNVERIFIED
  "reason":       "ratio=0.05, kept=0, claim=UNVERIFIED",
  // optional, additive diagnostics (downstream may ignore):
  "signals":      { },            // raw history numbers
  "flags":        [ ],            // e.g. ["ABUSE_RATIO", "PROMISE_TO_ABUSER"]
  "confidence":   0.82            // the Investigator's own rule confidence
}
```
Required keys (frozen): `genuineness`, `claim_status`, `reason`.

## 3. Economist output — `decide(verdict, reader_output, profile) -> dict`
```jsonc
{
  "action":         "REFUND",     // ACKNOWLEDGE | COUPON | WALLET_CREDIT | REFUND | ESCALATE
  "refund_type":    "KEEP_ITEM",  // PICKUP | KEEP_ITEM | NONE
  "coupon_percent": 0,            // 0 | 20 | 50
  "wallet_credit":  0,            // AED, or 0
  "escalate":       false,
  "email_trigger":  true,         // true ONLY for COUPON/REFUND/WALLET_CREDIT
  "reason":         "GENUINE + Damaged_Defective -> refund"  // internal, NOT customer-facing
}
```

## 4. Voice output
```jsonc
// voice.generate_reply(decision, message) -> str
// voice.fire_email(profile, decision, reply_text) -> { to, subject, body } | null
```

## 5. Consolidated pipeline response (what React consumes) — `pipeline.resolve(message, customer_id)`
The dashboard reads exactly these keys.
```jsonc
{
  "customer_id":  "C0005",
  "message":      "Hi, my milk arrived spoiled. Please help.",
  "reader":       { issue_type, frustration, confidence },
  "investigator": { genuineness, claim_status, reason, signals?, flags?, confidence? },
  "economist":    { action, refund_type, coupon_percent, wallet_credit, escalate, email_trigger, reason },
  "voice":        { reply_text, email },   // email is null when none fired
  "email_fired":  true,                    // convenience mirror of email_trigger
  "audit_id":     "A0007",                 // null when no money action
  "automation":   { escalated: false }     // feeds the automation-rate metric
}
```

> **Note on naming:** Plan §4.5 names the verdict/decision blocks `investigator`
> and `economist` (as above). The earlier README draft used `verdict`/`decision`
> with `reply_text`/`email_subject`/`email_body` at the top level; the
> implemented contract is this one (richer, nested under `voice`).

---

## Email truth table
| action | email_trigger | escalate |
|---|---|---|
| ACKNOWLEDGE | false | false |
| COUPON | true | false |
| WALLET_CREDIT | true | false |
| REFUND | true | false |
| ESCALATE | false | true |

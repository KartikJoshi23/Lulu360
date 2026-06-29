# Module 2 — The Investigator (trust engine)

Transparent rule engine. Decides **whether to trust the customer** (genuineness)
and **whether their "you promised me X" claim checks out** (claim status) —
using account history only, never message tone.

## Contract (frozen, Implementation Plan Sec.4.2)

```python
investigate(reader_output: dict, profile: dict, conversation_history=None) -> {
    # --- three REQUIRED keys (downstream reads these; never renamed) -------
    "genuineness":  "GENUINE" | "SUSPICIOUS" | "LIKELY_ABUSER",
    "claim_status": "CONFIRMED" | "CONTRADICTED" | "UNVERIFIED",
    "reason":       str,   # rich internal trace; never shown to the customer
    # --- OPTIONAL diagnostic keys (additive; safe to ignore) --------------
    "signals":      dict,  # raw history numbers that drove the verdict
    "flags":        list,  # machine-readable tags, e.g. ["ABUSE_RATIO"]
    "confidence":   float, # 0..1, how strongly the rules fired
}
```

The three required keys are exactly the frozen contract. The optional keys are
**additive** — the Economist and the React contract (Plan Sec.4.5) read only the
required keys and are completely unaffected.

- `reader_output` — the Module 1 dict `{issue_type, frustration, confidence}`.
  Accepted for the contract signature; **tone is deliberately not used**.
- `profile` — one `customers.csv` row as a dict, with `_archetype` already
  stripped (use `lookup_profile(customer_id)` or pass a mock dict).
- `conversation_history` *(optional)* — prior chat turns, newest-last. If a turn
  carries a resolved `claim_status`, it is reused instead of re-asking. Omitting
  it preserves the original stateless behaviour exactly.

## The hard edge case (the "fraud who called 4 times" question)

> *A man is a fraud but he has called 4 times and says he called 4 times and
> still didn't get the refund.*

The Investigator reports two facts truthfully and lets **the records decide**:

1. **Genuineness comes from history**, so he stays `LIKELY_ABUSER` no matter how
   many times he called or how convincing the message is.
2. **The claim is verified against our own notes**, not his word:
   - notes show we **denied** the remedy → `CONTRADICTED` (real customers
     **C0068 / C0209**) — calling 4× does not create a promise we never made;
   - a promise is **actually logged** → `CONFIRMED`, honoured *capped* with the
     abuse flagged (Plan Sec.4.7; customer **C0006**);
   - **no record either way** → `UNVERIFIED` — his asserted call count is his
     word, not ours; the Economist never auto-pays on `UNVERIFIED`.

Every branch carries a specific `reason`, so the call is always defensible.

## Robustness built in

- **Negation-aware note reading** — *"no promise was ever made"*, *"did not
  promise a refund"* are **not** read as a promise (the real NLP task M2 owns).
- **Never crashes** — `None`/`NaN`/`""`/`"abc"`/missing fields all coerce safely;
  a valid, reasoned verdict is always returned.
- **Chat-history aware** — an already-settled claim is not re-litigated.
- **Reason always matches the returned `claim_status`** (even under history
  override) — the explanation can never contradict the verdict.

## Public functions

| Function | Purpose |
|---|---|
| `assess_genuineness(profile)` | Check 1 — fraud verdict from history (tone-blind). |
| `verify_claim(profile, conversation_history=None)` | Check 2 — cross-examine the claim against our records (`prior_contacts_this_issue`, `prior_promise_logged`, `customer_care_notes`). |
| `investigate(reader_output, profile, conversation_history=None)` | Contract entry point; fuses both. |
| `lookup_profile(customer_id)` | Single profile lookup; drops `_archetype`. |

## Thresholds (yours to tune)

| Signal | LIKELY_ABUSER | SUSPICIOUS |
|---|---|---|
| refund-to-order ratio | >= 0.50 | >= 0.25 |
| items kept after refund | >= 3 | — |
| complaints last 30 days | >= 4 | >= 3 |
| account age (months) | — | <= 2 |
| is_first_purchase | — | True |

Re-running these rules over `customers.csv` reproduces the ground-truth
`_archetype` for **all 220 / 220** customers. The ratio rule requires at least
3 orders before a high refund ratio counts as abuse, so the two former boundary
cases (C0059, C0162 — ratio 0.50 from a single refund on a 2-order account) now
read as `SUSPICIOUS`, matching the ground truth and the Module 3 test mock.

Claim verification reproduces the plan's exact split: **33 CONFIRMED / 36
CONTRADICTED / 151 UNVERIFIED** — verified against the real file, not assumed.

## Run it standalone (works outside the whole project)

```bash
# built-in demo over the headline edge cases:
python investigator.py

# verdicts for specific real customers:
python investigator.py C0001 C0006 C0068 C0018

# full test suite (52 tests):
pytest backend/tests/test_investigator.py -q
```

The module needs only itself, `shared/enums.py`, and `backend/data/customers.csv`
— verified by running both the demo and the full test suite in an isolated copy
of just those files.

## Integration rules honoured

- **Tone-blind** — never reads `reader_output['frustration']` or the message.
- **No key renaming** — required output keys match the contract exactly.
- **JSON-safe** — all values are plain `str/int/float/bool/list/dict`.
- **`_archetype` quarantined** — never a feature, never in the output.
- **ASCII-only output** — reasons render on any console (no Unicode crashes).

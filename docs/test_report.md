# Test Report — LuluCare 360

Run: `cd <repo> && LULU_DISABLE_FLAN=1 pytest backend/tests/ -q`
(FLAN-T5 disabled → deterministic template replies; the Reader uses the trained
LSTM when `backend/models/` artifacts are present, else the keyword fallback.)

## Summary — **120 passed**

| Suite | Tests | Result | Covers |
|---|---:|---|---|
| `test_reader.py` | 16 | ✅ | contract keys/types, enum membership, `[0,1]` confidence, empty-input fallback, JSON-safe, active backend |
| `test_investigator.py` | 52 | ✅ | 3 fraud paths, 3 claim states, CONTRADICTED note bank, tone-blindness, C0006, `_archetype` quarantine, scored 218/220 vs archetype, negation/history robustness |
| `test_economist.py` | 28 | ✅ | 11 verified cases, tier-table order, logistics tree, escalation valve, email truth table, native-type casting |
| `test_voice.py` | 6 | ✅ | reply for every action, email iff `email_trigger`, ACKNOWLEDGE/ESCALATE never email, audit row per money action, template fallback |
| `test_pipeline.py` | 6 | ✅ | consolidated contract shape, JSON-safety, email rule end-to-end, 404 unknown id, stats |
| `test_cases_handbook.py` | 12 | ✅ | the 11 handbook cases through the assembled system + automation-rate target |

## Module-level (Plan §8.1)
- **Reader** — output is exactly `{issue_type, frustration, confidence}`; types correct; `issue_type` in the 7-enum; `frustration` in the 3-enum; confidence in `[0,1]`; empty/garbage never raises; backend-agnostic (LSTM or keyword).
- **Investigator** — all three genuineness paths and all three claim states; tone never changes the verdict; reproduces `_archetype` for **218/220** customers; claim distribution 33 CONFIRMED / 36 CONTRADICTED / 151 UNVERIFIED; never references `_archetype`.
- **Economist** — tier table evaluated top-to-bottom (first match wins); logistics tree all branches (perishable, resale ≥ 2000, cost > resale); escalation on both conditions; `coupon_percent ∈ {0,20,50}`; abuse never pays; every returned value native Python.
- **Voice** — a reply for every action; the polite ACKNOWLEDGE promises nothing; email present iff `email_trigger`; one audit row per money action; template fallback active with `LULU_DISABLE_FLAN=1`.

## Integration & contract (Plan §8.2)
- Reader keys feed the Investigator; verdict feeds the Economist; decision has every field the Voice reads.
- Consolidated response matches `shared/contracts.md` §5 key-for-key.
- `email=null` renders "no email" rather than crashing (front-end EmailPanel).
- Test isolation: the audit-log path resolves dynamically, so suites pass in any order.

## The handbook cases & automation rate (Plan §8.3–8.4)
All 11 verified cases pass through the assembled `decide → voice → email` path.

| # | Customer | Expected | Result |
|---|---|---|---|
| 1 | C0005 | REFUND + KEEP_ITEM | ✅ |
| 2 | C0013 | REFUND + PICKUP | ✅ |
| 3 | C0001 | ACKNOWLEDGE (abuser) | ✅ |
| 4 | C0004 | ACKNOWLEDGE (UNVERIFIED) | ✅ |
| 5 | C0034 | REFUND + KEEP_ITEM (CONFIRMED) | ✅ |
| 6 | C0032 | REFUND + KEEP_ITEM (economics) | ✅ |
| 7 | C0016 | COUPON 20% (first purchase) | ✅ |
| 8 | C0020 | ACKNOWLEDGE (low value) | ✅ |
| 9 | C0059 | ESCALATE | ✅ |
| 10 | C0018 | REFUND + PICKUP (calm defect) | ✅ |
| 11 | C0006 | REFUND + PICKUP + ABUSE_FLAG | ✅ |

**Automation rate = 10/11 = 90.9%** (only C0059 escalates by design) — meets the ≥ 90% target.

## Known limitation (live pipeline)
The 11 cases above use the handbook's canonical **mocked** Reader/Investigator
inputs. On the live API the real LSTM classifies free text, so terse/ambiguous
messages can be misread (e.g. "fresh produce arrived spoiled" → Delivery instead
of Damaged_Defective), changing the downstream action. The confidence gate +
escalation valve are the designed mitigation; see `docs/trust_memo.md`.

# Trust Memo

**To:** Reem, VP Customer Experience
**From:** The LuluCare 360 team
**Re:** Autonomy boundary, failure modes, and the automation rate we chose

---

**Would I let LuluCare 360 act fully autonomously?** Mostly yes — but not
everywhere. We let it act on its own for the routine ~90%: clear genuine defects,
acknowledgements, and standard coupons/wallet-credits to trusted customers. We
require a human in the loop for three case types, because each is where a wrong
call is expensive or legally sensitive:

1. **Any `ESCALATE`** — high order value with shaky trust, or low Reader
   confidence on a high-value customer. The money or the relationship is too big
   to risk on an uncertain read.
2. **A `CONFIRMED` promise to a `LIKELY_ABUSER`** (e.g. C0006). We honour our own
   logged promise — reneging carries legal and reputational risk — but we cap it
   to exactly what was promised, flag the abuse, and ask a human *why* a promise
   was ever made to that account.
3. **Anything where Reader `confidence < 0.5`.** An unsure read on a costly
   decision is exactly when a person should look.

**One wrong call from our testing, honestly.** On a live end-to-end run, customer
C0005's message *"my fresh produce arrived spoiled and damaged"* was classified
by the Reader (LSTM) as **Delivery** rather than **Damaged_Defective** — the words
"arrived" and "spoiled" pulled it toward the delivery class — so the Economist
fell through to **ACKNOWLEDGE** instead of the correct **REFUND + KEEP_ITEM**.
Cause: a genuine NLU ambiguity on a short message, not a policy error (the policy
is correct given its input). Mitigation already in place: the confidence gate
routes low-confidence high-value cases to a human; longer/clearer messages
classify correctly (C0018's "cracked screen" → REFUND + PICKUP). This is the
single most important reason we do **not** run the Reader as an unsupervised
oracle on high-value money decisions.

**How we stop abusers — and protect the genuine.** Trust is computed from
*history, never tone*: the refund-to-order ratio, items kept after refund, and
complaint bursts. An abuser writes the angriest message of all, so anger earns
nothing — Rule 3 short-circuits `LIKELY_ABUSER` to `ACKNOWLEDGE` before any
value or frustration rule runs (C0001: ratio 0.83, HIGH CLV, furious → no
payout). We never pay on an `UNVERIFIED` "your rep promised me" claim (C0004).
Conversely, calm does not mean undeserving: a genuine defect is refunded even at
Low frustration (C0018). Scored against the ground-truth labels, the trust engine
matches **220 / 220 customers (100%)**: all **45 abusers caught**, **0 genuine
customers wrongly branded abusers**, and across all 630 messages **0 cases** where
a `LIKELY_ABUSER` was paid without a promise logged in our own records. So our
confidence that a genuine customer is never wrongly *denied at the trust step* is
effectively total; the only residual risk is upstream NLU misclassification
(above), which is precisely why the confidence gate and escalation valve exist.

**The automation rate we reached: 90.9%** (10 of 11 verified cases resolved
without a human; only C0059 escalates by design). We chose this balance
deliberately across three competing forces — protect revenue (don't over-pay
abusers), protect retention (don't under-serve genuine high-value customers), and
protect the team's time (don't over-escalate). Below ~90% the team stays buried
and the business case collapses; pushing far above it would mean auto-approving
the high-stakes, low-certainty cases that genuinely need a person. ~90% is where
the co-pilot does the heavy routine work and a human still owns the rare,
expensive judgement calls.

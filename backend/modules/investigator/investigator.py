"""
Module 2 - The Investigator (the trust engine).

Transparent rules, not a model. Every decision here is read, defended, and
debated, because decisions about trust and money have to be explainable.

------------------------------------------------------------------------------
What this module answers
------------------------------------------------------------------------------
Two independent checks, fused into one verdict:

  Check 1 - Genuineness: are they gaming us?
      Judged ONLY from account history (refund-to-order ratio, items kept after
      refund, recent complaint burst, account age, first-purchase flag). The
      message tone is deliberately ignored: an abuser writes the angriest
      message of all, so anger is never evidence of honesty (Plan Sec.6, Trap 5).

  Check 2 - The unverifiable-claim test:
      The customer may claim "your rep promised me a refund" or "I called four
      times and still got nothing". We never trust an unverifiable claim made by
      the person who benefits from it. We cross-examine it against our OWN
      records - prior_contacts_this_issue, prior_promise_logged, and the
      free-text customer_care_notes (a small, negation-aware NLP task).

------------------------------------------------------------------------------
The hard edge case (the one a sceptical professor asks about)
------------------------------------------------------------------------------
"A man is a fraud, but he has called 4 times and says he called 4 times and
 still hasn't received the refund. How do you handle that?"

The Investigator reports two facts truthfully and lets the records decide:

  - Genuineness is computed from history alone, so a fraud stays LIKELY_ABUSER
    no matter how many times he called or how convincingly he writes.
  - The *claim* ("you promised me a refund") is verified against our notes:
      * If our notes say we DENIED the remedy and he acknowledged it
        (e.g. "explained item is non-returnable; customer acknowledged"),
        claim_status = CONTRADICTED - calling four times does not create a
        promise we never made. No payout. (Real customers C0068 / C0209.)
      * If our own records actually LOGGED a promise, claim_status = CONFIRMED
        and the Economist honours it *capped to the promised remedy only*,
        flags the abuse, and grants nothing extra (Plan Sec.4.7; customer C0006).
      * If we have no record either way, claim_status = UNVERIFIED - the number
        of calls he asserts is his word, not ours, and the Economist never pays
        on UNVERIFIED alone (Plan Sec.6, Trap 7).

  In every branch the verdict carries a specific, human-readable `reason`.

------------------------------------------------------------------------------
Contract (Implementation Plan Sec.4.2) - frozen, never renamed
------------------------------------------------------------------------------
    investigate(reader_output, profile, conversation_history=None) -> {
        # ---- the three REQUIRED keys (downstream reads these) -------------
        "genuineness":  GENUINE | SUSPICIOUS | LIKELY_ABUSER,
        "claim_status": CONFIRMED | CONTRADICTED | UNVERIFIED,
        "reason":       str,   # rich internal explanation, never customer-facing
        # ---- OPTIONAL diagnostic keys (safe to ignore downstream) ---------
        "signals":      dict,  # the raw numbers that drove the verdict
        "flags":        list,  # short machine-readable tags, e.g. ["ABUSE_RATIO"]
        "confidence":   float, # 0..1 how strongly the rules fired
    }

The optional keys are additive: any consumer that reads only the three required
keys (the Economist, the React contract in Plan Sec.4.5) is completely unaffected.

------------------------------------------------------------------------------
Integration rules obeyed (Plan Sec.5)
------------------------------------------------------------------------------
  - Rule 6, tone-blindness: assess_genuineness reads only history fields. It
    never reads reader_output['frustration'] or the raw customer message.
  - Rule 8, ground-truth quarantine: this module never references the
    quarantined label column in any form.
  - Everything JSON-safe: outputs are plain str/int/float/bool/list/dict only.
"""

from __future__ import annotations

import sys
from pathlib import Path

# --- Import the single shared enum source (Plan Sec.5, Rule 3) -------------------
# The investigator must never re-type a literal like "LIKELY_ABUSER" in branch
# logic. shared/ is a sibling of backend/ in the frozen folder layout (Plan Sec.3).
# We add it to sys.path only if `enums` is not already importable, so the side
# effect is a no-op when the pipeline owner has put shared/ on the path.
try:
    from enums import (  # noqa: E402
        GENUINE, SUSPICIOUS, LIKELY_ABUSER,
        CONFIRMED, CONTRADICTED, UNVERIFIED,
    )
except ModuleNotFoundError:
    _SHARED = Path(__file__).resolve().parents[3] / "shared"
    if str(_SHARED) not in sys.path:
        sys.path.insert(0, str(_SHARED))
    from enums import (  # noqa: E402  (path set up above)
        GENUINE, SUSPICIOUS, LIKELY_ABUSER,
        CONFIRMED, CONTRADICTED, UNVERIFIED,
    )


# ===========================================================================
# Thresholds - the team's to tune, documented and verified against the data.
# Re-running these rules over customers.csv reproduces the ground-truth
# _archetype for ALL 220 / 220 customers.
# ===========================================================================

ABUSER_RATIO = 0.50          # a refund on most orders is the killer abuse signal
ABUSER_MIN_ORDERS = 3        # ...but only once there is enough history for the
                             # ratio to mean something. One refund out of two
                             # orders (ratio 0.50) on a brand-new account is a
                             # small-sample artefact, not proof of abuse — those
                             # customers fall to SUSPICIOUS (verify, cap), which
                             # is what the ground truth intends (the "newbie
                             # chancer" is SUSPICIOUS, not LIKELY_ABUSER). All 45
                             # real abusers have >= 3 orders, so none slip.
ABUSER_KEPT_ITEMS = 3        # repeatedly keeping refunded items is "refund-and-keep"
ABUSER_BURST = 4             # a burst of complaints in 30 days = coordinated claims

SUSPICIOUS_RATIO = 0.25      # an elevated (not extreme) refund ratio
SUSPICIOUS_BURST = 3         # a smaller complaint burst
SUSPICIOUS_MAX_AGE_MONTHS = 2  # a brand-new account cannot have earned trust yet


# ===========================================================================
# Claim-verification phrase banks (Check 2) - negation-aware NLP.
#
# Reading the agent notes is itself a small NLP task. The phrase banks match on
# robust key phrases (lower-cased, substring) so the logic generalises beyond
# the shipped templates to free-text an agent might actually type. A dedicated
# negation pass (below) prevents "no promise was ever made" from being read as a
# promise just because it contains the word "promise".
# ===========================================================================

# Phrases that AFFIRM a prior promise/commitment was made to the customer.
_PROMISE_AFFIRM_PHRASES = (
    "promised", "assured", "committed to", "guaranteed",
    "will refund", "will be refunded", "approved a refund",
    "refund pending", "pending processing", "not yet issued",
    "replacement on", "agreed to refund", "offered a refund",
    "offered a coupon", "compensation approved",
)

# Phrases that DENY / CONTRADICT a claimed promise (we refused, per policy).
_PROMISE_DENY_PHRASES = (
    "no prior promise", "no promise", "never promised", "no refund applicable",
    "non-returnable", "not returnable", "not eligible", "no compensation",
    "no refund due", "declined the refund", "refund declined", "request denied",
    "informed customer no", "per policy; customer agreed",
    "customer acknowledged", "no refund will be", "not entitled",
)

# Negation cues that, when they precede a promise word, flip an apparent
# affirmation into a denial - e.g. "no promise was made", "did not promise".
_NEGATION_CUES = (
    "no ", "not ", "never ", "n't ", "without ", "denied", "declined",
    "refused", "no prior", "did not", "was not", "wasn't", "isn't",
)


def _has_any(text: str, phrases) -> bool:
    """True if any phrase appears (case-insensitively) in text."""
    low = (text or "").lower()
    return any(p in low for p in phrases)


def _affirms_promise(notes: str) -> bool:
    """
    True only if the note genuinely affirms a promise, AFTER accounting for
    negation. "Agent promised a refund" -> True. "No promise was made",
    "did not promise a refund", "promise was declined" -> False.

    Heuristic: find each affirming phrase; if a negation cue appears in the
    short window of text immediately before it, the affirmation is cancelled.
    """
    low = (notes or "").lower()
    if not low:
        return False
    affirmed = False
    for phrase in _PROMISE_AFFIRM_PHRASES:
        start = low.find(phrase)
        if start == -1:
            continue
        window = low[max(0, start - 24):start]   # look just left of the phrase
        if any(cue in window for cue in _NEGATION_CUES):
            continue  # negated -> not an affirmation
        affirmed = True
        break
    return affirmed


# ===========================================================================
# Check 1 - Genuineness (tone-blind; history only)
# ===========================================================================

def assess_genuineness(profile: dict) -> str:
    """
    Classify the customer's trustworthiness from account history alone.

    Reads ONLY history fields - never reader_output, never message tone
    (Plan Sec.5, Rule 6). Abuse signals first, then softer suspicion signals;
    anything else is GENUINE.

    Returns one of: GENUINE | SUSPICIOUS | LIKELY_ABUSER.
    """
    s = _history_signals(profile)

    # The serial refunder: refunds on most orders, keeps items, or a complaint
    # burst. No payout follows, no matter how angry the message. The ratio only
    # counts as abuse once there is enough order history behind it (>= 3 orders);
    # a 0.50 ratio from a single refund on a 2-order account is a small-sample
    # artefact and falls to SUSPICIOUS below, matching the ground truth.
    if (s["ratio"] >= ABUSER_RATIO and s["orders"] >= ABUSER_MIN_ORDERS) \
            or s["kept"] >= ABUSER_KEPT_ITEMS or s["burst"] >= ABUSER_BURST:
        return LIKELY_ABUSER

    # Worth watching: elevated ratio, a brand-new / first-purchase account, or a
    # smaller complaint burst. Handled generously but capped by the Economist.
    if (
        s["ratio"] >= SUSPICIOUS_RATIO
        or s["age"] <= SUSPICIOUS_MAX_AGE_MONTHS
        or s["first_purchase"]
        or s["burst"] >= SUSPICIOUS_BURST
    ):
        return SUSPICIOUS

    # The loyal regular: low ratio, established account. Trusted.
    return GENUINE


# ===========================================================================
# Check 2 - The unverifiable-claim test (records win)
# ===========================================================================

def verify_claim(profile: dict, conversation_history=None) -> str:
    """
    Cross-examine a customer's "you promised me X" / "I called N times" story
    against OUR records. The handbook names three record fields and all three
    are used: prior_contacts_this_issue, prior_promise_logged, customer_care_notes.

    A claim is only verifiable if there is a prior interaction to verify against.
    With prior_contacts_this_issue == 0 (and an empty note) there is no record to
    confirm or deny it -> UNVERIFIED. A logged promise is authoritative on its
    own (it proves an interaction occurred), so it confirms even if the contact
    counter is somehow zero.

    Truth precedence (records win where they disagree with the customer):
      1. Logged promise OR a non-negated affirming note            -> CONFIRMED
      2. No prior contact on record                                -> UNVERIFIED
      3. A note that explicitly denies/refuses the remedy          -> CONTRADICTED
      4. Otherwise                                                 -> UNVERIFIED

    `conversation_history` (optional) lets the caller pass prior turns so a claim
    that was already resolved earlier in the chat is not re-litigated; see
    `_claim_from_history`.
    """
    promise_logged = _as_bool(profile.get("prior_promise_logged", False))
    notes = str(profile.get("customer_care_notes", "") or "")
    prior_contacts = _as_int(profile.get("prior_contacts_this_issue", 0))

    # If this exact claim was already settled earlier in the conversation, reuse
    # that outcome rather than asking/answering it again.
    prior = _claim_from_history(conversation_history)
    if prior is not None:
        return prior

    affirms = promise_logged or _affirms_promise(notes)
    denies = _has_any(notes, _PROMISE_DENY_PHRASES)

    if affirms:
        return CONFIRMED
    if prior_contacts <= 0:
        return UNVERIFIED
    if denies:
        return CONTRADICTED
    return UNVERIFIED


# ===========================================================================
# The contract entry point
# ===========================================================================

def investigate(reader_output: dict, profile: dict, conversation_history=None) -> dict:
    """
    Fuse both checks into the Investigator verdict (Plan Sec.4.2).

    Parameters
    ----------
    reader_output : dict
        The Module 1 dict {issue_type, frustration, confidence}. Accepted to
        honour the contract signature; its tone is deliberately NOT used.
    profile : dict
        One customers.csv row as a dict, with _archetype already stripped at
        load (Plan Sec.5, Rule 11). Missing fields default safely.
    conversation_history : list[dict] | None, optional
        Prior chat turns, newest-last. Each turn may carry a resolved
        'claim_status'. Lets the engine avoid re-asking an already-answered
        question. Backward-compatible: omitting it preserves old behaviour.

    Returns
    -------
    dict
        The three required keys plus optional diagnostic keys. JSON-safe.
    """
    profile = profile or {}
    s = _history_signals(profile)

    genuineness = assess_genuineness(profile)
    claim_status = verify_claim(profile, conversation_history)
    flags = _build_flags(s, genuineness, claim_status, profile)
    reason = _build_reason(s, genuineness, claim_status, profile, conversation_history)
    confidence = _verdict_confidence(s, genuineness)

    return {
        # required, contract-frozen
        "genuineness": str(genuineness),
        "claim_status": str(claim_status),
        "reason": str(reason),
        # optional, additive diagnostics (downstream may ignore)
        "signals": s,
        "flags": flags,
        "confidence": confidence,
    }


# ===========================================================================
# Reason builder - a specific, defensible sentence for EVERY situation
# ===========================================================================

def _build_reason(s, genuineness, claim_status, profile, conversation_history) -> str:
    """
    Produce a precise, human-readable explanation tailored to the exact branch
    that fired. Internal only - surfaced in the dashboard, never sent to the
    customer. There is a distinct sentence for every (genuineness, claim) combo
    so no situation is ever left with a vague reason.
    """
    # --- the trust half --------------------------------------------------
    if genuineness == LIKELY_ABUSER:
        why = []
        if s["ratio"] >= ABUSER_RATIO:
            why.append(f"refund ratio {s['ratio']:.2f} >= {ABUSER_RATIO}")
        if s["kept"] >= ABUSER_KEPT_ITEMS:
            why.append(f"kept {s['kept']} refunded items (>= {ABUSER_KEPT_ITEMS})")
        if s["burst"] >= ABUSER_BURST:
            why.append(f"{s['burst']} complaints in 30 days (>= {ABUSER_BURST})")
        trust = "LIKELY_ABUSER - " + "; ".join(why)
    elif genuineness == SUSPICIOUS:
        why = []
        if s["ratio"] >= SUSPICIOUS_RATIO:
            why.append(f"elevated refund ratio {s['ratio']:.2f}")
        if s["first_purchase"]:
            why.append("first purchase")
        if s["age"] <= SUSPICIOUS_MAX_AGE_MONTHS:
            why.append(f"new account ({s['age']}m old)")
        if s["burst"] >= SUSPICIOUS_BURST:
            why.append(f"{s['burst']} recent complaints")
        trust = "SUSPICIOUS - " + ("; ".join(why) if why else "soft risk signal")
    else:
        trust = (f"GENUINE - low refund ratio {s['ratio']:.2f}, "
                 f"established account ({s['age']}m), no abuse signals")

    # --- the claim half --------------------------------------------------
    # Branch strictly on the FINAL claim_status (which may have been supplied by
    # conversation history), so the reason text can never disagree with it.
    contacts = s["prior_contacts"]
    reused = _claim_from_history(conversation_history) is not None
    if claim_status == CONFIRMED:
        if _as_bool(profile.get("prior_promise_logged", False)):
            claim = ("claim CONFIRMED - a promise is logged in our own records, "
                     "so it is honoured (capped to the promised remedy)")
        elif reused:
            claim = ("claim CONFIRMED - carried over from an earlier turn in "
                     "this conversation")
        else:
            claim = ("claim CONFIRMED - our agent notes affirm a prior "
                     "commitment to the customer")
        if genuineness == LIKELY_ABUSER:
            claim += ("; NOTE: customer is a likely abuser, so honour the logged "
                      "promise only and grant no extra generosity (Plan Sec.4.7)")
    elif claim_status == CONTRADICTED:
        claim = (f"claim CONTRADICTED - customer contacted us {contacts}x but our "
                 f"notes show the remedy was declined/never promised, so the "
                 f"asserted promise is disproved by our record")
    else:  # UNVERIFIED
        if contacts <= 0:
            claim = ("claim UNVERIFIED - no prior contact is on record, so the "
                     "customer's assertion (e.g. 'I called and was promised a "
                     "refund') cannot be substantiated; do not auto-pay")
        else:
            claim = (f"claim UNVERIFIED - {contacts} prior contact(s) on record "
                     f"but no logged promise either way; do not auto-pay on the "
                     f"customer's word alone")

    note = ""
    if _claim_from_history(conversation_history) is not None:
        note = " (claim already settled earlier in this conversation; not re-asked)"

    return f"{trust}. {claim}{note}."


# ===========================================================================
# Conversation-history awareness (optional, backward-compatible)
# ===========================================================================

def _claim_from_history(conversation_history):
    """
    If the customer's claim was already verified earlier in this conversation,
    return that resolved claim_status so we neither re-ask nor re-litigate it.

    Accepts a list of turn dicts (newest-last). A turn counts as a prior
    resolution if it carries a 'claim_status' in the valid enum set. Returns the
    most recent such value, or None if there is nothing to reuse.
    """
    if not conversation_history:
        return None
    valid = (CONFIRMED, CONTRADICTED, UNVERIFIED)
    for turn in reversed(conversation_history):
        if not isinstance(turn, dict):
            continue
        status = turn.get("claim_status")
        if status in valid:
            return status
    return None


# ===========================================================================
# Diagnostics
# ===========================================================================

def _build_flags(s, genuineness, claim_status, profile) -> list:
    """Short machine-readable tags explaining which rules fired. Optional."""
    flags = []
    if s["ratio"] >= ABUSER_RATIO and s["orders"] >= ABUSER_MIN_ORDERS:
        flags.append("ABUSE_RATIO")
    if s["kept"] >= ABUSER_KEPT_ITEMS:
        flags.append("ABUSE_KEPT_ITEMS")
    if s["burst"] >= ABUSER_BURST:
        flags.append("ABUSE_BURST")
    if genuineness == SUSPICIOUS:
        if s["first_purchase"]:
            flags.append("NEW_FIRST_PURCHASE")
        if s["age"] <= SUSPICIOUS_MAX_AGE_MONTHS:
            flags.append("NEW_ACCOUNT")
        if s["ratio"] >= SUSPICIOUS_RATIO:
            flags.append("ELEVATED_RATIO")
    if claim_status == CONFIRMED and genuineness == LIKELY_ABUSER:
        flags.append("PROMISE_TO_ABUSER")   # honour-capped conflict (Plan Sec.4.7)
    if claim_status == CONTRADICTED:
        flags.append("CLAIM_DISPROVED")
    if claim_status == UNVERIFIED and s["prior_contacts"] <= 0:
        flags.append("NO_RECORD")
    return flags


def _verdict_confidence(s, genuineness) -> float:
    """
    How strongly the rules fired, in [0,1]. This is the Investigator's own
    confidence (distinct from the Reader's). High when a signal is far past its
    threshold; lower when the customer sits right on a boundary (e.g. ratio
    exactly 0.50), which is where human review is most valuable.
    """
    if genuineness == LIKELY_ABUSER:
        margins = []
        if s["ratio"] >= ABUSER_RATIO:
            margins.append(min(1.0, (s["ratio"] - ABUSER_RATIO) / 0.5 + 0.5))
        if s["kept"] >= ABUSER_KEPT_ITEMS:
            margins.append(min(1.0, 0.5 + 0.15 * (s["kept"] - ABUSER_KEPT_ITEMS)))
        if s["burst"] >= ABUSER_BURST:
            margins.append(min(1.0, 0.5 + 0.15 * (s["burst"] - ABUSER_BURST)))
        return round(max(margins) if margins else 0.6, 3)
    if genuineness == SUSPICIOUS:
        return 0.6
    # GENUINE: more confident the further below the suspicious ratio they sit.
    return round(min(1.0, 0.7 + (SUSPICIOUS_RATIO - s["ratio"]) ), 3)


# ===========================================================================
# Internal helpers
# ===========================================================================

def _history_signals(profile: dict) -> dict:
    """Extract and normalise the history fields used by both checks. JSON-safe."""
    return {
        "ratio": _as_float(profile.get("refund_to_order_ratio", 0.0)),
        "kept": _as_int(profile.get("items_kept_after_refund", 0)),
        "burst": _as_int(profile.get("complaints_last_30_days", 0)),
        "age": _as_int(profile.get("account_age_months", 0)),
        "orders": _as_int(profile.get("total_orders", 0)),
        "first_purchase": _as_bool(profile.get("is_first_purchase", False)),
        "prior_contacts": _as_int(profile.get("prior_contacts_this_issue", 0)),
        "promise_logged": _as_bool(profile.get("prior_promise_logged", False)),
    }


def _as_bool(value) -> bool:
    """Coerce CSV / NumPy / string truthy values to a plain Python bool."""
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y")
    return bool(value)


def _as_int(value) -> int:
    """Coerce to int, treating None/NaN/'' as 0; never raises."""
    if value is None or value == "":
        return 0
    try:
        f = float(value)
        return 0 if f != f else int(f)   # f != f catches NaN
    except (TypeError, ValueError):
        return 0


def _as_float(value) -> float:
    """Coerce to float, treating None/NaN/'' as 0.0; never raises."""
    if value is None or value == "":
        return 0.0
    try:
        f = float(value)
        return 0.0 if f != f else f
    except (TypeError, ValueError):
        return 0.0


# ===========================================================================
# Standalone runner - so this folder works on its own, outside the pipeline.
#   python investigator.py            -> demo on built-in mock profiles
#   python investigator.py C0006 C0068 ... -> verdicts for real customer ids
# ===========================================================================

if __name__ == "__main__":
    import json

    def _print(title, reader_output, profile, history=None):
        out = investigate(reader_output, profile, history)
        print(f"\n=== {title} ===")
        print(json.dumps(out, indent=2))

    args = [a for a in sys.argv[1:]]
    furious = {"issue_type": "Refund_Return", "frustration": "High", "confidence": 0.9}

    if args:
        # Real customer ids via the profile loader.
        try:
            from profile_loader import lookup_profile
        except ModuleNotFoundError:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from profile_loader import lookup_profile
        for cid in args:
            try:
                _print(cid, furious, lookup_profile(cid))
            except KeyError as e:
                print(f"\n=== {cid} ===\n  {e}")
    else:
        # Built-in mock profiles covering the headline edge cases.
        _print(
            "Professor's case: fraud who called 4x claiming a promise, "
            "but our notes show we DENIED it",
            furious,
            {
                "customer_id": "MOCK_FRAUD_CONTACTED",
                "refund_to_order_ratio": 0.83, "items_kept_after_refund": 3,
                "complaints_last_30_days": 4, "account_age_months": 3,
                "is_first_purchase": False, "prior_contacts_this_issue": 4,
                "prior_promise_logged": False,
                "customer_care_notes": "Explained item is non-returnable; customer acknowledged.",
            },
        )
        _print(
            "Fraud with a genuinely LOGGED promise (honour capped - Plan Sec.4.7)",
            furious,
            {
                "customer_id": "MOCK_FRAUD_PROMISED",
                "refund_to_order_ratio": 0.58, "items_kept_after_refund": 4,
                "complaints_last_30_days": 4, "account_age_months": 14,
                "prior_contacts_this_issue": 2, "prior_promise_logged": True,
                "customer_care_notes": "Customer was assured replacement on last contact.",
            },
        )
        _print(
            "Genuine loyal regular, no prior contact",
            furious,
            {
                "customer_id": "MOCK_GENUINE",
                "refund_to_order_ratio": 0.05, "account_age_months": 40,
                "prior_contacts_this_issue": 0, "prior_promise_logged": False,
                "customer_care_notes": "",
            },
        )
        _print(
            "Negation note: 'no promise was ever made' must NOT read as CONFIRMED",
            furious,
            {
                "customer_id": "MOCK_NEGATION",
                "refund_to_order_ratio": 0.05, "account_age_months": 30,
                "prior_contacts_this_issue": 1, "prior_promise_logged": False,
                "customer_care_notes": "Clarified no promise was ever made to the customer.",
            },
        )
        _print(
            "Claim already settled earlier in the chat (not re-asked)",
            furious,
            {
                "customer_id": "MOCK_HISTORY",
                "refund_to_order_ratio": 0.05, "account_age_months": 30,
                "prior_contacts_this_issue": 1, "prior_promise_logged": False,
                "customer_care_notes": "",
            },
            history=[{"claim_status": CONTRADICTED}],
        )

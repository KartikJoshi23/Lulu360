"""
Module 3 — The Economist.  Resolution & Refund-Economics Engine.

The real, verified deliverable (extracted from lulucare360_module3/economist.ipynb,
owner: Krishna Mathur · AS25DXB018). Replaces the earlier integration placeholder.

Text-free (Integration Rule 7): returns structured fields only; ``reason`` is an
internal explanation, never the customer-facing reply (that is the Voice's job).

Contract (Plan 4.3 — frozen keys):
    decide(verdict, reader_output, profile) ->
        {action, refund_type, coupon_percent, wallet_credit,
         escalate, email_trigger, reason}

All returned values are native Python types (str/int/bool) — JSON-safe.
"""

import os
import re
import sys

# ---------------------------------------------------------------------------
# Enum constants — single source of truth (shared/enums.py). A local fallback
# keeps the module runnable standalone (e.g. Colab) per the original notebook.
# ---------------------------------------------------------------------------
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from shared.enums import (
        GENUINE, SUSPICIOUS, LIKELY_ABUSER,
        CONFIRMED, CONTRADICTED, UNVERIFIED,
        ACTION_ACKNOWLEDGE, ACTION_COUPON, ACTION_WALLET_CREDIT,
        ACTION_REFUND, ACTION_ESCALATE, EMAIL_ACTIONS,
        REFUND_PICKUP, REFUND_KEEP_ITEM, REFUND_NONE,
        FRUST_HIGH, FRUST_MEDIUM,
        TIER_GOLD, TIER_SILVER, TIER_PLATINUM,
        ISSUE_DAMAGED_DEFECTIVE, ISSUE_GENERAL_QUERY,
        VALUE_HIGH, VALUE_MEDIUM, VALUE_LOW,
    )
except Exception:  # pragma: no cover - standalone fallback
    GENUINE, SUSPICIOUS, LIKELY_ABUSER = "GENUINE", "SUSPICIOUS", "LIKELY_ABUSER"
    CONFIRMED, CONTRADICTED, UNVERIFIED = "CONFIRMED", "CONTRADICTED", "UNVERIFIED"
    ACTION_ACKNOWLEDGE, ACTION_COUPON = "ACKNOWLEDGE", "COUPON"
    ACTION_WALLET_CREDIT, ACTION_REFUND, ACTION_ESCALATE = "WALLET_CREDIT", "REFUND", "ESCALATE"
    EMAIL_ACTIONS = (ACTION_COUPON, ACTION_REFUND, ACTION_WALLET_CREDIT)
    REFUND_PICKUP, REFUND_KEEP_ITEM, REFUND_NONE = "PICKUP", "KEEP_ITEM", "NONE"
    FRUST_HIGH, FRUST_MEDIUM = "High", "Medium"
    TIER_GOLD, TIER_SILVER, TIER_PLATINUM = "Gold", "Silver", "Platinum"
    ISSUE_DAMAGED_DEFECTIVE, ISSUE_GENERAL_QUERY = "Damaged_Defective", "General_Query"
    VALUE_HIGH, VALUE_MEDIUM, VALUE_LOW = "HIGH", "MEDIUM", "LOW"


# ===========================================================================
# Tunable policy knobs (documented and defended in the trust memo)
# ===========================================================================
COUPON_STANDARD = 20            # default goodwill coupon (%)
COUPON_GENEROUS = 50            # high-frustration, high-value coupon (%)
ALLOWED_COUPONS = (0, COUPON_STANDARD, COUPON_GENEROUS)

# Wallet-credit amounts by value band, in AED. TUNABLE policy choice.
WALLET_CREDIT_BY_BAND = {VALUE_LOW: 50, VALUE_MEDIUM: 100, VALUE_HIGH: 200}

NEW_ACCOUNT_MAX_MONTHS = 2      # 'newbie' threshold
HIGH_RESALE_THRESHOLD = 2000    # costly resalable goods always worth recovering
ESCALATE_ORDER_VALUE = 5000     # large-money threshold for the escalation valve
LOW_CONFIDENCE = 0.5            # Reader confidence floor for the escalation valve


# ===========================================================================
# 1. value_band — customer value classification (never grants trust)
# ===========================================================================
def value_band(p: dict) -> str:
    # Platinum or very high lifetime value -> HIGH
    if p["loyalty_tier"] == TIER_PLATINUM or p["clv_estimate"] >= 40000:
        return VALUE_HIGH
    # Gold/Silver or moderate CLV -> MEDIUM
    if p["loyalty_tier"] in (TIER_GOLD, TIER_SILVER) or p["clv_estimate"] >= 12000:
        return VALUE_MEDIUM
    # Everything else -> LOW
    return VALUE_LOW


# ===========================================================================
# 2. refund_logistics — keep vs pickup tree (only called for an actual refund)
# ===========================================================================
def refund_logistics(p: dict) -> str:
    # 1) Perishable / hygiene goods cannot be resold -> collecting is pure waste.
    if p["is_perishable_or_hygiene"]:
        return REFUND_KEEP_ITEM
    # 2) Costly resalable goods always worth recovering.
    if p["resale_value"] >= HIGH_RESALE_THRESHOLD:
        return REFUND_PICKUP
    # 3) Weigh freight against recoverable value.
    if p["reverse_logistics_cost"] > p["resale_value"]:
        return REFUND_KEEP_ITEM   # shipping it back costs more than it is worth
    return REFUND_PICKUP


# ===========================================================================
# 3. should_escalate — the escalation valve (fires on exactly two conditions)
# ===========================================================================
def should_escalate(verdict: dict, reader: dict, p: dict, proposed_refund: bool) -> bool:
    # Large money + uncertain trust -> warrants a human's eyes.
    if proposed_refund and verdict["genuineness"] == SUSPICIOUS and p["order_value"] > ESCALATE_ORDER_VALUE:
        return True
    # Unsure about a valuable customer -> risks a costly wrong call.
    if reader["confidence"] < LOW_CONFIDENCE and value_band(p) == VALUE_HIGH:
        return True
    return False


# ===========================================================================
# CONFIRMED-promise helpers — honour exactly what an agent LOGGED
# ===========================================================================
def _extract_percent(text: str):
    """Pull a logged coupon percentage out of the verdict reason/notes, if any."""
    m = re.search(r"(\d{1,3})\s*%", text)
    return int(m.group(1)) if m else None


def _confirmed_remedy(verdict: dict):
    """
    Honour exactly what an agent LOGGED. Default to a full REFUND; only switch to
    COUPON when the logged note explicitly mentions a coupon/discount/%. A logged
    promise is OUR record (unfakeable by the customer).
    """
    reason = str(verdict.get("reason", "")).lower()
    pct = _extract_percent(reason)
    mentions_coupon = ("coupon" in reason) or ("discount" in reason) or (pct is not None)
    if mentions_coupon:
        if pct in (COUPON_STANDARD, COUPON_GENEROUS):
            cp = pct
        elif (pct or 0) >= 35:
            cp = COUPON_GENEROUS
        else:
            cp = COUPON_STANDARD
        return ACTION_COUPON, cp, 0
    return ACTION_REFUND, 0, 0


# ===========================================================================
# 4. choose_action — the 8-rule remediation tier table (first match wins)
#    ORDER IS THE ANTI-ABUSE PRECEDENCE. Do not reorder.
# ===========================================================================
def choose_action(verdict: dict, reader: dict, p: dict):
    g = verdict["genuineness"]
    claim = verdict["claim_status"]
    issue = reader["issue_type"]
    frust = reader["frustration"]
    band = value_band(p)

    if issue == ISSUE_GENERAL_QUERY:
        return ACTION_ACKNOWLEDGE, 0, 0, "General_Query service inquiry -> answer helpfully, no compensation flow"

    # 1) CONTRADICTED — our notes disprove the claim. No payout, no email.
    if claim == CONTRADICTED:
        return ACTION_ACKNOWLEDGE, 0, 0, "claim CONTRADICTED by our records -> respond from record, no payout"

    # 2) CONFIRMED — an agent LOGGED a promise. Honour exactly what was logged.
    if claim == CONFIRMED:
        action, cp, wc = _confirmed_remedy(verdict)
        if g == LIKELY_ABUSER:
            # C0006 conflict: honour our record, but cap to promised scope only.
            note = ("CONFIRMED logged promise honoured; genuineness=LIKELY_ABUSER -> "
                    "ABUSE_FLAG: capped to promised remedy, no extra remediation, normal logistics")
            return action, cp, wc, note
        return action, cp, wc, "CONFIRMED logged promise -> honour exactly what was logged"

    # 3) LIKELY_ABUSER — history (not tone) shows gaming. Anger is not evidence.
    if g == LIKELY_ABUSER:
        return ACTION_ACKNOWLEDGE, 0, 0, "genuineness LIKELY_ABUSER -> acknowledge only, abuse never pays"

    # 4) New account / first purchase — generous but capped.
    if p["is_first_purchase"] or p["account_age_months"] <= NEW_ACCOUNT_MAX_MONTHS:
        return ACTION_COUPON, COUPON_STANDARD, 0, "new/first-purchase account -> generous-but-capped coupon, verify"

    # 5) GENUINE + clear product failure -> REFUND.
    #    Placed BEFORE frustration rules so a calm genuine defect is never downgraded.
    if g == GENUINE and issue == ISSUE_DAMAGED_DEFECTIVE:
        return ACTION_REFUND, 0, 0, "GENUINE + Damaged_Defective -> refund (logistics by economics)"

    # 6) GENUINE + High frustration + HIGH value -> generous coupon.
    if g == GENUINE and frust == FRUST_HIGH and band == VALUE_HIGH:
        return ACTION_COUPON, COUPON_GENEROUS, 0, "GENUINE + High frustration + HIGH value -> generous coupon"

    # 7) GENUINE + Medium frustration -> standard goodwill, scaled by value.
    if g == GENUINE and frust == FRUST_MEDIUM:
        if band == VALUE_LOW:
            return ACTION_WALLET_CREDIT, 0, WALLET_CREDIT_BY_BAND[VALUE_LOW], "GENUINE + Medium + LOW value -> flat wallet credit"
        return ACTION_COUPON, COUPON_STANDARD, 0, "GENUINE + Medium frustration -> standard coupon"

    # 8) Everything else (GENUINE, Low, routine) -> acknowledge.
    return ACTION_ACKNOWLEDGE, 0, 0, "GENUINE routine / Low frustration -> acknowledge or small gesture"


# ===========================================================================
# 5. decide — the single public orchestrator (fixed order)
# ===========================================================================
def decide(verdict: dict, reader: dict, p: dict) -> dict:
    # a) pick the action + amounts from the tier table
    action, coupon_percent, wallet_credit, note = choose_action(verdict, reader, p)

    # b) logistics only matter for an actual refund; otherwise NONE
    refund_type = refund_logistics(p) if action == ACTION_REFUND else REFUND_NONE

    # c) escalation valve — evaluated against the *proposed* action
    escalate = should_escalate(verdict, reader, p, proposed_refund=(action == ACTION_REFUND))
    if escalate:
        action = ACTION_ESCALATE
        note = note + " | OVERRIDE: escalated to human (high stakes + low certainty)"

    # d) email fires for money actions ONLY, recomputed AFTER escalation
    email_trigger = action in EMAIL_ACTIONS

    # e) cast EVERYTHING to native Python types (pandas gives NumPy scalars)
    return {
        "action": str(action),
        "refund_type": str(refund_type),
        "coupon_percent": int(coupon_percent),
        "wallet_credit": int(wallet_credit),
        "escalate": bool(escalate),
        "email_trigger": bool(email_trigger),
        "reason": str(note),
    }

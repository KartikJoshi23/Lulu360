"""
Module 3 - The Economist.  *** PLACEHOLDER - owned by the Economist team. ***

Not our deliverable. We ship a faithful reading of the handbook rules
(Tables 26-31) and the Plan's remediation-tier order (Table 14, first-match
wins) so the Voice pipeline produces realistic decisions to speak and email.
The Economist team replaces this with their tuned, tested version.

Text-free (Integration Rule 7): returns structured fields only; `reason` is an
internal explanation, never the customer-facing reply.

Contract (Plan 4.3):
    decide(verdict, reader_output, profile) ->
        {action, refund_type, coupon_percent, wallet_credit,
         escalate, email_trigger, reason}
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from shared import enums as E  # noqa: E402


def value_band(p: dict) -> str:
    if p["loyalty_tier"] == "Platinum" or p["clv_estimate"] >= 40000:
        return "HIGH"
    if p["loyalty_tier"] in ("Gold", "Silver") or p["clv_estimate"] >= 12000:
        return "MEDIUM"
    return "LOW"


def refund_logistics(p: dict) -> str:
    if p["is_perishable_or_hygiene"]:
        return E.KEEP_ITEM                       # cannot resell -> never collect
    if p["resale_value"] >= 2000:
        return E.PICKUP                          # costly resalable -> recover
    if p["reverse_logistics_cost"] > p["resale_value"]:
        return E.KEEP_ITEM                       # shipping back > worth
    return E.PICKUP


def should_escalate(verdict, reader, p, proposed_refund) -> bool:
    if proposed_refund and verdict["genuineness"] == E.SUSPICIOUS and p["order_value"] > 5000:
        return True                              # large money + uncertain trust
    if reader["confidence"] < 0.5 and value_band(p) == "HIGH":
        return True                              # unsure about a valuable customer
    return False


def _choose_action(verdict, reader, p):
    """Returns (action, coupon_percent, wallet_credit). Decision order is the
    Plan's Table 14, evaluated top to bottom; first match wins."""
    g = verdict["genuineness"]
    claim = verdict["claim_status"]
    band = value_band(p)
    frust = reader["frustration"]

    # 1. Our records contradict the claim -> respond from the record, no payout.
    if claim == E.CONTRADICTED:
        return E.ACKNOWLEDGE, 0, 0

    # 2. A logged promise is our own record -> honour it. Outranks abuser status
    #    for the promised item only (Plan 4.7 / C0006), but grants nothing extra.
    if claim == E.CONFIRMED:
        return E.REFUND, 0, 0

    # 3. Known abuser -> polite acknowledgement, no payout, regardless of value.
    if g == E.LIKELY_ABUSER:
        return E.ACKNOWLEDGE, 0, 0

    # 4. Suspicious newbie -> generous but capped, with verification.
    if g == E.SUSPICIOUS and (p.get("is_first_purchase") or p["account_age_months"] <= 2):
        return E.COUPON, 20, 0

    # 5. Genuine clear product failure -> refund (logistics tree applied later).
    if g == E.GENUINE and reader["issue_type"] == E.ISSUE_TYPES[1]:  # Damaged_Defective
        return E.REFUND, 0, 0

    # 6. Genuine + high frustration + high value -> the generous lane.
    if g == E.GENUINE and frust == "High" and band == "HIGH":
        return E.REFUND, 0, 0

    # 7. Genuine + medium frustration -> mid gesture, scaled by value.
    if g == E.GENUINE and frust == "Medium":
        if band == "LOW":
            return E.COUPON, 20, 0
        return E.WALLET_CREDIT, 0, 200

    # 8. Genuine, low frustration, routine -> acknowledge / small gesture.
    return E.ACKNOWLEDGE, 0, 0


def decide(verdict: dict, reader: dict, p: dict) -> dict:
    action, coupon, credit = _choose_action(verdict, reader, p)

    refund_type = refund_logistics(p) if action == E.REFUND else E.NONE
    escalate = should_escalate(verdict, reader, p, action == E.REFUND)
    if escalate:
        action = E.ESCALATE
        refund_type = E.NONE
        coupon, credit = 0, 0

    email_trigger = action in E.EMAIL_ACTIONS    # the ONE email rule, set here

    reason = (f"genuineness={verdict['genuineness']}, claim={verdict['claim_status']}, "
              f"value={value_band(p)}, frustration={reader['frustration']} -> {action}")
    if verdict["genuineness"] == E.LIKELY_ABUSER and verdict["claim_status"] == E.CONFIRMED:
        reason += " | ABUSE FLAG: logged promise honoured (capped); no extra generosity"

    return {
        "action": action,
        "refund_type": refund_type,
        "coupon_percent": int(coupon),
        "wallet_credit": int(credit),
        "escalate": bool(escalate),
        "email_trigger": bool(email_trigger),
        "reason": reason,
    }

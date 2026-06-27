"""
backend/pipeline.py - orchestrates the one-directional flow and assembles the
consolidated response the React dashboard consumes.

Owned by the Voice sub-team (it "drives integration", Plan 2.4). It only wires
modules together by their frozen contracts; it contains no business thresholds.

    (message, customer_id)
        -> Reader      {issue_type, frustration, confidence}
        -> Investigator{genuineness, claim_status, reason}
        -> Economist   {action, refund_type, coupon_percent, wallet_credit,
                        escalate, email_trigger, reason}
        -> Voice       reply_text (+ email if email_trigger)
        -> Audit log   (one row per money action)

Returns exactly the keys in Plan 4.5 / Handbook Table 13 - nothing more,
nothing fewer (Trap 11). Everything is JSON-safe (Integration Rule 2).
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.data.loader import lookup_profile                      # noqa: E402
from backend.modules.reader.reader import read_message             # noqa: E402
from backend.modules.investigator.investigator import investigate  # noqa: E402
from backend.modules.economist.economist import decide             # noqa: E402
from backend.modules.voice import voice                            # noqa: E402


def resolve(message: str, customer_id: str) -> dict:
    """Run the full pipeline for one complaint and return the consolidated
    response. Raises KeyError(customer_id) for an unknown customer so the API
    can answer 404."""
    profile = lookup_profile(customer_id)
    if profile is None:
        raise KeyError(customer_id)

    reader = read_message(message)                       # Module 1
    verdict = investigate(reader, profile)               # Module 2
    decision = decide(verdict, reader, profile)          # Module 3
    reply = voice.generate_reply(decision, message)           # Module 4
    email, audit_id = voice.fire_email(profile, decision, reply)  # Module 4 + audit

    return {
        "customer_id": str(customer_id),
        "message": message,
        "reader": {
            "issue_type": str(reader["issue_type"]),
            "frustration": str(reader["frustration"]),
            "confidence": float(reader["confidence"]),
        },
        "investigator": {
            "genuineness":  str(verdict["genuineness"]),
            "claim_status": str(verdict["claim_status"]),
            "reason":       str(verdict["reason"]),
            "signals":      verdict.get("signals"),
            "flags":        verdict.get("flags"),
            "confidence":   float(verdict["confidence"]) if verdict.get("confidence") is not None else None,
        },
        "economist": {
            "action": str(decision["action"]),
            "refund_type": str(decision["refund_type"]),
            "coupon_percent": int(decision["coupon_percent"]),
            "wallet_credit": int(decision["wallet_credit"]),
            "escalate": bool(decision["escalate"]),
            "email_trigger": bool(decision["email_trigger"]),
            "reason": str(decision["reason"]),
        },
        "voice": {
            "reply_text": str(reply),
            "email": email,                  # {to, subject, body} or None
        },
        "email_fired": bool(email is not None),   # convenience mirror
        "audit_id": audit_id,                     # None when no money action
        "automation": {"escalated": bool(decision["escalate"])},
    }

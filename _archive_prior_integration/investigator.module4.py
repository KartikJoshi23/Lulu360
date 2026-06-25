"""
Module 2 - The Investigator.  *** PLACEHOLDER - owned by the Investigator team. ***

Not our deliverable. We ship the handbook's reference rules (Tables 22-25) so
the pipeline produces sensible verdicts for the Voice demo. The Investigator
team replaces this with their tuned, tested version.

Tone-blind (Integration Rule 6): genuineness is computed from history only;
it never reads reader_output['frustration'] or the raw message.

Contract (Plan 4.2):
    investigate(reader_output, profile) ->
        {genuineness, claim_status, reason}
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from shared import enums as E  # noqa: E402


def assess_genuineness(p: dict) -> str:
    ratio = p["refund_to_order_ratio"]
    kept = p["items_kept_after_refund"]
    burst = p["complaints_last_30_days"]
    if ratio >= 0.5 or kept >= 3 or burst >= 4:
        return E.LIKELY_ABUSER
    if ratio >= 0.25 or p["account_age_months"] <= 2 or burst >= 3:
        return E.SUSPICIOUS
    return E.GENUINE


def verify_claim(p: dict) -> str:
    notes = str(p.get("customer_care_notes", "")).lower()
    if p.get("prior_promise_logged") or "promised" in notes or "assured" in notes:
        return E.CONFIRMED
    if "no refund" in notes or "non-returnable" in notes or "no prior promise" in notes:
        return E.CONTRADICTED
    return E.UNVERIFIED


def investigate(reader_output: dict, profile: dict) -> dict:
    g = assess_genuineness(profile)
    c = verify_claim(profile)
    return {
        "genuineness": g,
        "claim_status": c,
        "reason": (f"ratio={profile['refund_to_order_ratio']}, "
                   f"kept={profile['items_kept_after_refund']}, claim={c}"),
    }

"""
test_cases_handbook.py — the provided handbook test cases + automation rate
(Implementation Plan §3, §8.3 / §8.4).

Runs all 11 verified cases through the assembled decide() -> voice path using the
handbook's canonical mocked Reader/Investigator inputs, asserts each expected
resolution, and asserts the automation rate meets the >= 90% target.

    pytest backend/tests/test_cases_handbook.py -q
"""

import os
import sys

os.environ.setdefault("LULU_DISABLE_FLAN", "1")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest  # noqa: E402

from backend.modules.economist.economist import decide   # noqa: E402
from backend.modules.voice import voice                  # noqa: E402
from shared.enums import (                                # noqa: E402
    GENUINE, SUSPICIOUS, LIKELY_ABUSER, CONFIRMED, UNVERIFIED,
    ACTION_ESCALATE, EMAIL_ACTIONS,
)

DD = "Damaged_Defective"


def _r(issue, frust, conf=0.9):
    return {"issue_type": issue, "frustration": frust, "confidence": conf}


def _v(g, c, reason=""):
    return {"genuineness": g, "claim_status": c, "reason": reason}


# customer economics (only the fields the Economist reads)
P = {
    "C0005": {"loyalty_tier": "Gold", "clv_estimate": 37040, "order_value": 394, "is_first_purchase": False, "account_age_months": 27, "is_perishable_or_hygiene": True, "resale_value": 0, "reverse_logistics_cost": 108},
    "C0013": {"loyalty_tier": "Silver", "clv_estimate": 9445, "order_value": 53678, "is_first_purchase": False, "account_age_months": 60, "is_perishable_or_hygiene": False, "resale_value": 34890, "reverse_logistics_cost": 78},
    "C0001": {"loyalty_tier": "Silver", "clv_estimate": 159720, "order_value": 9164, "is_first_purchase": False, "account_age_months": 1, "is_perishable_or_hygiene": False, "resale_value": 5956, "reverse_logistics_cost": 101},
    "C0004": {"loyalty_tier": "Silver", "clv_estimate": 14467, "order_value": 4204, "is_first_purchase": False, "account_age_months": 41, "is_perishable_or_hygiene": False, "resale_value": 1891, "reverse_logistics_cost": 291},
    "C0034": {"loyalty_tier": "Bronze", "clv_estimate": 33188, "order_value": 871, "is_first_purchase": False, "account_age_months": 33, "is_perishable_or_hygiene": True, "resale_value": 0, "reverse_logistics_cost": 68},
    "C0032": {"loyalty_tier": "Silver", "clv_estimate": 57134, "order_value": 410, "is_first_purchase": False, "account_age_months": 49, "is_perishable_or_hygiene": False, "resale_value": 164, "reverse_logistics_cost": 180},
    "C0016": {"loyalty_tier": "Gold", "clv_estimate": 16176, "order_value": 2293, "is_first_purchase": True, "account_age_months": 0, "is_perishable_or_hygiene": False, "resale_value": 917, "reverse_logistics_cost": 253},
    "C0020": {"loyalty_tier": "Bronze", "clv_estimate": 4959, "order_value": 224, "is_first_purchase": False, "account_age_months": 61, "is_perishable_or_hygiene": True, "resale_value": 0, "reverse_logistics_cost": 118},
    "C0059": {"loyalty_tier": "Platinum", "clv_estimate": 114588, "order_value": 24392, "is_first_purchase": False, "account_age_months": 1, "is_perishable_or_hygiene": False, "resale_value": 14635, "reverse_logistics_cost": 212},
    "C0018": {"loyalty_tier": "Platinum", "clv_estimate": 117030, "order_value": 66383, "is_first_purchase": False, "account_age_months": 20, "is_perishable_or_hygiene": False, "resale_value": 43148, "reverse_logistics_cost": 121},
    "C0006": {"loyalty_tier": "Silver", "clv_estimate": 25926, "order_value": 445, "is_first_purchase": False, "account_age_months": 14, "is_perishable_or_hygiene": False, "resale_value": 200, "reverse_logistics_cost": 121},
}

# (case_no, customer, verdict, reader, expected_action, expected_refund_type)
CASES = [
    (1, "C0005", _v(GENUINE, UNVERIFIED), _r(DD, "High"), "REFUND", "KEEP_ITEM"),
    (2, "C0013", _v(GENUINE, UNVERIFIED), _r(DD, "High"), "REFUND", "PICKUP"),
    (3, "C0001", _v(LIKELY_ABUSER, UNVERIFIED, "ratio 0.833"), _r("Delivery", "High", 0.90), "ACKNOWLEDGE", "NONE"),
    (4, "C0004", _v(GENUINE, UNVERIFIED, "claims a promise"), _r("Refund_Return", "Low"), "ACKNOWLEDGE", "NONE"),
    (5, "C0034", _v(GENUINE, CONFIRMED, "assured replacement"), _r("Refund_Return", "Medium"), "REFUND", "KEEP_ITEM"),
    (6, "C0032", _v(GENUINE, UNVERIFIED), _r(DD, "Medium"), "REFUND", "KEEP_ITEM"),
    (7, "C0016", _v(SUSPICIOUS, UNVERIFIED), _r("Delivery", "High", 0.85), "COUPON", "NONE"),
    (8, "C0020", _v(GENUINE, UNVERIFIED), _r("App_Technical", "Low"), "ACKNOWLEDGE", "NONE"),
    (9, "C0059", _v(SUSPICIOUS, UNVERIFIED), _r(DD, "High", 0.45), "ESCALATE", "NONE"),
    (10, "C0018", _v(GENUINE, UNVERIFIED), _r(DD, "Low", 0.93), "REFUND", "PICKUP"),
    (11, "C0006", _v(LIKELY_ABUSER, CONFIRMED, "assured replacement"), _r("Refund_Return", "High"), "REFUND", "PICKUP"),
]


@pytest.mark.parametrize("n,cid,v,r,exp_action,exp_refund", CASES,
                         ids=[f"case{n:02d}_{cid}" for n, cid, *_ in CASES])
def test_handbook_case(n, cid, v, r, exp_action, exp_refund):
    d = decide(v, r, P[cid])
    assert d["action"] == exp_action, f"case {n} {cid}: action {d['action']} != {exp_action}"
    assert d["refund_type"] == exp_refund, f"case {n} {cid}: refund {d['refund_type']} != {exp_refund}"
    # email rule must hold end-to-end
    reply = voice.generate_reply(d, "handbook")
    email = voice.fire_email(P[cid] | {"customer_id": cid}, d, reply)
    assert (email is not None) == (d["action"] in EMAIL_ACTIONS)


def test_automation_rate_meets_target():
    automated = sum(1 for _, cid, v, r, *_ in CASES if decide(v, r, P[cid])["action"] != ACTION_ESCALATE)
    rate = automated / len(CASES)
    assert rate >= 0.90, f"automation rate {rate:.1%} below 90% target"
    # Exactly one case (C0059) is designed to escalate.
    assert automated == len(CASES) - 1

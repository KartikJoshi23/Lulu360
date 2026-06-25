"""
backend/scripts/handbook_report.py — run the 11 verified handbook cases through
the assembled system (Economist decision -> Voice reply + email + audit) and
report the automation rate.

These cases use the canonical MOCKED Reader/Investigator inputs from the
handbook (Plan Sec.6), which is how the cases are defined; the live API uses the
real LSTM Reader + Investigator. FLAN-T5 is disabled for deterministic replies.

    python backend/scripts/handbook_report.py
"""

import os
import sys

os.environ.setdefault("LULU_DISABLE_FLAN", "1")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.modules.economist.economist import decide   # noqa: E402
from backend.modules.voice import voice                  # noqa: E402
from shared.enums import (                                # noqa: E402
    GENUINE, SUSPICIOUS, LIKELY_ABUSER, CONFIRMED, UNVERIFIED,
    ACTION_ESCALATE,
)


def R(issue, frust, conf=0.9):
    return {"issue_type": issue, "frustration": frust, "confidence": conf}


def V(g, c, reason=""):
    return {"genuineness": g, "claim_status": c, "reason": reason}


DD = "Damaged_Defective"
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

# (case, customer, verdict, reader, expected_action, expected_refund)
CASES = [
    (1, "C0005", V(GENUINE, UNVERIFIED), R(DD, "High"), "REFUND", "KEEP_ITEM"),
    (2, "C0013", V(GENUINE, UNVERIFIED), R(DD, "High"), "REFUND", "PICKUP"),
    (3, "C0001", V(LIKELY_ABUSER, UNVERIFIED, "ratio 0.833"), R("Delivery", "High", 0.90), "ACKNOWLEDGE", "NONE"),
    (4, "C0004", V(GENUINE, UNVERIFIED, "claims a promise"), R("Refund_Return", "Low"), "ACKNOWLEDGE", "NONE"),
    (5, "C0034", V(GENUINE, CONFIRMED, "assured replacement"), R("Refund_Return", "Medium"), "REFUND", "KEEP_ITEM"),
    (6, "C0032", V(GENUINE, UNVERIFIED), R(DD, "Medium"), "REFUND", "KEEP_ITEM"),
    (7, "C0016", V(SUSPICIOUS, UNVERIFIED), R("Delivery", "High", 0.85), "COUPON", "NONE"),
    (8, "C0020", V(GENUINE, UNVERIFIED), R("App_Technical", "Low"), "ACKNOWLEDGE", "NONE"),
    (9, "C0059", V(SUSPICIOUS, UNVERIFIED), R(DD, "High", 0.45), "ESCALATE", "NONE"),
    (10, "C0018", V(GENUINE, UNVERIFIED), R(DD, "Low", 0.93), "REFUND", "PICKUP"),
    (11, "C0006", V(LIKELY_ABUSER, CONFIRMED, "assured replacement"), R("Refund_Return", "High"), "REFUND", "PICKUP"),
]


def main() -> None:
    passed = 0
    automated = 0
    print(f"{'#':>2}  {'cust':<6} {'action':<12} {'refund':<10} {'email':<6} {'expect':<12} result")
    print("-" * 70)
    for n, cid, v, r, exp_action, exp_refund in CASES:
        d = decide(v, r, P[cid])
        reply = voice.generate_reply(d, "handbook case")
        voice.fire_email(P[cid] | {"customer_id": cid}, d, reply)
        ok = d["action"] == exp_action and d["refund_type"] == exp_refund
        passed += ok
        automated += d["action"] != ACTION_ESCALATE
        print(f"{n:>2}  {cid:<6} {d['action']:<12} {d['refund_type']:<10} "
              f"{str(d['email_trigger']):<6} {exp_action:<12} {'PASS' if ok else 'FAIL'}")
    total = len(CASES)
    print("-" * 70)
    print(f"Handbook cases passed : {passed}/{total}")
    print(f"Automated (non-escalate): {automated}/{total}")
    print(f"AUTOMATION RATE        : {automated / total * 100:.1f}%  (target >= 90%)")


if __name__ == "__main__":
    main()

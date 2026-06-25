"""
test_economist.py — Module 3 unit tests (Implementation Plan Sec.8).

Faithful pytest port of lulucare360_module3/test_economist.ipynb:
  - 11 verified case tests pinned to real customers.csv rows
  - 3 supplementary branch tests (Rule 6, Rule 7, CONTRADICTED)
  - structural assertions (exact keys, enum membership, native types, email rule)
  - value_band + refund_logistics unit tests

Run from the repo root:  pytest backend/tests/test_economist.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.modules.economist.economist import (  # noqa: E402
    decide,
    value_band,
    refund_logistics,
)
from shared.enums import (  # noqa: E402
    GENUINE, SUSPICIOUS, LIKELY_ABUSER,
    CONFIRMED, CONTRADICTED, UNVERIFIED,
    ACTION_ACKNOWLEDGE, ACTION_COUPON, ACTION_WALLET_CREDIT,
    ACTION_REFUND, ACTION_ESCALATE, ACTIONS, EMAIL_ACTIONS,
    REFUND_PICKUP, REFUND_KEEP_ITEM, REFUND_NONE, REFUND_TYPES,
    ISSUE_DAMAGED_DEFECTIVE, VALUE_HIGH, VALUE_MEDIUM, VALUE_LOW,
)


# --- helper constructors ----------------------------------------------------
def reader(issue, frust="Medium", conf=0.9):
    return {"issue_type": issue, "frustration": frust, "confidence": conf}


def verdict(g, c, reason=""):
    return {"genuineness": g, "claim_status": c, "reason": reason}


# Real customers.csv profiles (only the fields the Economist reads; _archetype stripped)
PROFILES = {
    "C0005": {"loyalty_tier": "Gold", "clv_estimate": 37040, "order_value": 394,
              "is_first_purchase": False, "account_age_months": 27,
              "is_perishable_or_hygiene": True, "resale_value": 0, "reverse_logistics_cost": 108},
    "C0013": {"loyalty_tier": "Silver", "clv_estimate": 9445, "order_value": 53678,
              "is_first_purchase": False, "account_age_months": 60,
              "is_perishable_or_hygiene": False, "resale_value": 34890, "reverse_logistics_cost": 78},
    "C0001": {"loyalty_tier": "Silver", "clv_estimate": 159720, "order_value": 9164,
              "is_first_purchase": False, "account_age_months": 1,
              "is_perishable_or_hygiene": False, "resale_value": 5956, "reverse_logistics_cost": 101},
    "C0004": {"loyalty_tier": "Silver", "clv_estimate": 14467, "order_value": 4204,
              "is_first_purchase": False, "account_age_months": 41,
              "is_perishable_or_hygiene": False, "resale_value": 1891, "reverse_logistics_cost": 291},
    "C0034": {"loyalty_tier": "Bronze", "clv_estimate": 33188, "order_value": 871,
              "is_first_purchase": False, "account_age_months": 33,
              "is_perishable_or_hygiene": True, "resale_value": 0, "reverse_logistics_cost": 68},
    "C0032": {"loyalty_tier": "Silver", "clv_estimate": 57134, "order_value": 410,
              "is_first_purchase": False, "account_age_months": 49,
              "is_perishable_or_hygiene": False, "resale_value": 164, "reverse_logistics_cost": 180},
    "C0016": {"loyalty_tier": "Gold", "clv_estimate": 16176, "order_value": 2293,
              "is_first_purchase": True, "account_age_months": 0,
              "is_perishable_or_hygiene": False, "resale_value": 917, "reverse_logistics_cost": 253},
    "C0020": {"loyalty_tier": "Bronze", "clv_estimate": 4959, "order_value": 224,
              "is_first_purchase": False, "account_age_months": 61,
              "is_perishable_or_hygiene": True, "resale_value": 0, "reverse_logistics_cost": 118},
    "C0059": {"loyalty_tier": "Platinum", "clv_estimate": 114588, "order_value": 24392,
              "is_first_purchase": False, "account_age_months": 1,
              "is_perishable_or_hygiene": False, "resale_value": 14635, "reverse_logistics_cost": 212},
    "C0018": {"loyalty_tier": "Platinum", "clv_estimate": 117030, "order_value": 66383,
              "is_first_purchase": False, "account_age_months": 20,
              "is_perishable_or_hygiene": False, "resale_value": 43148, "reverse_logistics_cost": 121},
    "C0006": {"loyalty_tier": "Silver", "clv_estimate": 25926, "order_value": 445,
              "is_first_purchase": False, "account_age_months": 14,
              "is_perishable_or_hygiene": False, "resale_value": 200, "reverse_logistics_cost": 121},
}


# ===========================================================================
# The 11 verified case tests
# ===========================================================================
def test_case_01_C0005_perishable_defect_refund_keep():
    d = decide(verdict(GENUINE, UNVERIFIED), reader(ISSUE_DAMAGED_DEFECTIVE, "High"), PROFILES["C0005"])
    assert d["action"] == ACTION_REFUND
    assert d["refund_type"] == REFUND_KEEP_ITEM
    assert d["email_trigger"] is True
    assert d["escalate"] is False


def test_case_02_C0013_electronics_refund_pickup():
    d = decide(verdict(GENUINE, UNVERIFIED), reader(ISSUE_DAMAGED_DEFECTIVE, "High"), PROFILES["C0013"])
    assert d["action"] == ACTION_REFUND
    assert d["refund_type"] == REFUND_PICKUP
    assert d["email_trigger"] is True


def test_case_03_C0001_abuser_never_pays_despite_high_value():
    d = decide(verdict(LIKELY_ABUSER, UNVERIFIED, "ratio 0.833"), reader("Delivery", "High", conf=0.90), PROFILES["C0001"])
    assert d["action"] == ACTION_ACKNOWLEDGE
    assert d["email_trigger"] is False
    assert d["coupon_percent"] == 0 and d["wallet_credit"] == 0


def test_case_04_C0004_unverified_claim_is_not_a_payout():
    d = decide(verdict(GENUINE, UNVERIFIED, "customer says a rep promised a refund"), reader("Refund_Return", "Low"), PROFILES["C0004"])
    assert d["action"] != ACTION_REFUND
    assert d["action"] == ACTION_ACKNOWLEDGE
    assert d["email_trigger"] is False


def test_case_05_C0034_confirmed_promise_perishable_refund_keep():
    d = decide(verdict(GENUINE, CONFIRMED, "Customer was assured replacement on last contact."), reader("Refund_Return", "Medium"), PROFILES["C0034"])
    assert d["action"] == ACTION_REFUND
    assert d["refund_type"] == REFUND_KEEP_ITEM
    assert d["email_trigger"] is True


def test_case_06_C0032_economics_keep_item():
    d = decide(verdict(GENUINE, UNVERIFIED), reader(ISSUE_DAMAGED_DEFECTIVE, "Medium"), PROFILES["C0032"])
    assert d["action"] == ACTION_REFUND
    assert d["refund_type"] == REFUND_KEEP_ITEM
    assert d["email_trigger"] is True


def test_case_07_C0016_first_purchase_generous_but_capped_no_escalate():
    d = decide(verdict(SUSPICIOUS, UNVERIFIED), reader("Delivery", "High", conf=0.85), PROFILES["C0016"])
    assert d["action"] == ACTION_COUPON
    assert d["coupon_percent"] == 20
    assert d["escalate"] is False
    assert d["email_trigger"] is True


def test_case_08_C0020_low_value_genuine_low_frustration_acknowledge():
    d = decide(verdict(GENUINE, UNVERIFIED), reader("App_Technical", "Low"), PROFILES["C0020"])
    assert d["action"] == ACTION_ACKNOWLEDGE
    assert d["email_trigger"] is False


def test_case_09_C0059_escalates_no_email():
    d = decide(verdict(SUSPICIOUS, UNVERIFIED), reader(ISSUE_DAMAGED_DEFECTIVE, "High", conf=0.45), PROFILES["C0059"])
    assert d["action"] == ACTION_ESCALATE
    assert d["escalate"] is True
    assert d["email_trigger"] is False


def test_case_10_C0018_calm_genuine_highvalue_defect_still_refund():
    d = decide(verdict(GENUINE, UNVERIFIED), reader(ISSUE_DAMAGED_DEFECTIVE, "Low", conf=0.93), PROFILES["C0018"])
    assert d["action"] == ACTION_REFUND
    assert d["refund_type"] == REFUND_PICKUP
    assert d["email_trigger"] is True


def test_case_11_C0006_abuser_with_logged_promise_honoured_but_capped():
    d = decide(verdict(LIKELY_ABUSER, CONFIRMED, "Customer was assured replacement on last contact."), reader("Refund_Return", "High"), PROFILES["C0006"])
    assert d["action"] == ACTION_REFUND
    assert d["refund_type"] == REFUND_PICKUP
    assert d["email_trigger"] is True
    assert "ABUSE" in d["reason"].upper()


# ===========================================================================
# Supplementary branch tests
# ===========================================================================
def test_rule6_high_frustration_high_value_generous_coupon():
    d = decide(verdict(GENUINE, UNVERIFIED), reader("Billing", "High"), PROFILES["C0018"])
    assert d["action"] == ACTION_COUPON
    assert d["coupon_percent"] == 50


def test_rule7_medium_low_value_wallet_credit():
    d = decide(verdict(GENUINE, UNVERIFIED), reader("Billing", "Medium"), PROFILES["C0020"])
    assert d["action"] == ACTION_WALLET_CREDIT
    assert d["wallet_credit"] == 50
    assert d["email_trigger"] is True


def test_contradicted_acknowledge_no_email():
    d = decide(verdict(GENUINE, CONTRADICTED, "no refund per policy"), reader("Refund_Return", "High"), PROFILES["C0004"])
    assert d["action"] == ACTION_ACKNOWLEDGE
    assert d["email_trigger"] is False


# ===========================================================================
# Structural assertions across a mock matrix
# ===========================================================================
_ALL_MOCKS = [
    (verdict(GENUINE, UNVERIFIED), reader(ISSUE_DAMAGED_DEFECTIVE, "High"), PROFILES["C0005"]),
    (verdict(LIKELY_ABUSER, UNVERIFIED), reader("Delivery", "High", 0.9), PROFILES["C0001"]),
    (verdict(SUSPICIOUS, UNVERIFIED), reader("Delivery", "High", 0.85), PROFILES["C0016"]),
    (verdict(GENUINE, CONFIRMED, "replacement"), reader("Refund_Return", "Medium"), PROFILES["C0034"]),
    (verdict(SUSPICIOUS, UNVERIFIED), reader(ISSUE_DAMAGED_DEFECTIVE, "High", 0.45), PROFILES["C0059"]),
    (verdict(GENUINE, UNVERIFIED), reader("App_Technical", "Low"), PROFILES["C0020"]),
]
_EXPECTED_KEYS = {"action", "refund_type", "coupon_percent", "wallet_credit", "escalate", "email_trigger", "reason"}


@pytest.mark.parametrize("v,r,p", _ALL_MOCKS)
def test_structural_contract(v, r, p):
    d = decide(v, r, p)
    assert set(d.keys()) == _EXPECTED_KEYS
    assert d["action"] in ACTIONS
    assert d["refund_type"] in REFUND_TYPES
    assert d["coupon_percent"] in (0, 20, 50)
    assert d["wallet_credit"] >= 0
    assert d["email_trigger"] == (d["action"] in EMAIL_ACTIONS)


@pytest.mark.parametrize("v,r,p", _ALL_MOCKS)
def test_all_returned_values_are_native_python_types(v, r, p):
    d = decide(v, r, p)
    for k, val in d.items():
        assert type(val).__module__ == "builtins", f"{k} is not native Python: {type(val)}"
    assert isinstance(d["escalate"], bool)
    assert isinstance(d["email_trigger"], bool)
    assert isinstance(d["coupon_percent"], int)
    assert isinstance(d["wallet_credit"], int)


# ===========================================================================
# value_band + refund_logistics unit tests
# ===========================================================================
def test_value_band():
    assert value_band(PROFILES["C0018"]) == VALUE_HIGH
    assert value_band(PROFILES["C0032"]) == VALUE_HIGH      # clv 57134 >= 40000
    assert value_band(PROFILES["C0016"]) == VALUE_MEDIUM    # Gold
    assert value_band(PROFILES["C0020"]) == VALUE_LOW       # Bronze, clv 4959


def test_refund_logistics():
    assert refund_logistics(PROFILES["C0005"]) == REFUND_KEEP_ITEM   # perishable
    assert refund_logistics(PROFILES["C0013"]) == REFUND_PICKUP      # resale 34890
    assert refund_logistics(PROFILES["C0032"]) == REFUND_KEEP_ITEM   # freight 180 > 164
    assert refund_logistics(PROFILES["C0006"]) == REFUND_PICKUP      # resale 200 > freight 121

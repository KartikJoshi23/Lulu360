"""
test_investigator.py — Module 2 unit tests (Implementation Plan §8.1).

Covered, per the contract's "Required tests" row:
  - all 3 fraud paths (ratio / kept / burst -> LIKELY_ABUSER;
    ratio / age / first / burst -> SUSPICIOUS; else GENUINE)
  - all 3 claim states, including the CONTRADICTED note bank
  - tone never changes the verdict (Rule 6, tone-blindness)
  - C0006: abuser + logged promise -> LIKELY_ABUSER + CONFIRMED (Trap 2)
  - _archetype is never referenced by the module and absent from every profile
  - output schema: exact keys, plain-str (JSON-safe) values, valid enum members
  - scored against _archetype on the real data (expect ~218/220)

Run from the repo root:  pytest backend/tests/test_investigator.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# --- make the module + shared enums importable regardless of CWD -------------
_ROOT = Path(__file__).resolve().parents[2]
for p in (_ROOT, _ROOT / "backend" / "modules" / "investigator", _ROOT / "shared"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backend.modules.investigator.investigator import (  # noqa: E402
    assess_genuineness,
    verify_claim,
    investigate,
)
from backend.modules.investigator.profile_loader import lookup_profile  # noqa: E402
from enums import (  # noqa: E402
    GENUINE,
    SUSPICIOUS,
    LIKELY_ABUSER,
    CONFIRMED,
    CONTRADICTED,
    UNVERIFIED,
    GENUINENESS_VALUES,
    CLAIM_STATUS_VALUES,
)

_CUSTOMERS_CSV = _ROOT / "backend" / "data" / "customers.csv"

# A throwaway Reader output. Its tone is HIGH on purpose, so any test that still
# expects GENUINE proves the Investigator ignores tone.
_FURIOUS = {"issue_type": "Refund_Return", "frustration": "High", "confidence": 0.9}
_CALM = {"issue_type": "General_Query", "frustration": "Low", "confidence": 0.8}


def _profile(**over) -> dict:
    """A clean GENUINE baseline profile, overridable per test."""
    base = {
        "customer_id": "CTEST",
        "account_age_months": 40,
        "loyalty_tier": "Gold",
        "refund_to_order_ratio": 0.05,
        "items_kept_after_refund": 0,
        "complaints_last_30_days": 0,
        "is_first_purchase": False,
        "prior_promise_logged": False,
        "customer_care_notes": "",
        "prior_contacts_this_issue": 0,
        "order_value": 200,
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# Check 1 — the three fraud paths
# ---------------------------------------------------------------------------

class TestGenuineness:
    def test_genuine_loyal_regular(self):
        assert assess_genuineness(_profile()) == GENUINE

    def test_abuser_by_ratio(self):
        # The serial refunder: 6 orders, 5 refunds, kept 3, ratio 0.83.
        p = _profile(refund_to_order_ratio=0.833, items_kept_after_refund=3,
                     complaints_last_30_days=4)
        assert assess_genuineness(p) == LIKELY_ABUSER

    def test_abuser_by_kept_items_alone(self):
        p = _profile(refund_to_order_ratio=0.1, items_kept_after_refund=3)
        assert assess_genuineness(p) == LIKELY_ABUSER

    def test_abuser_by_complaint_burst_alone(self):
        p = _profile(refund_to_order_ratio=0.1, complaints_last_30_days=4)
        assert assess_genuineness(p) == LIKELY_ABUSER

    def test_suspicious_by_elevated_ratio(self):
        p = _profile(refund_to_order_ratio=0.30)
        assert assess_genuineness(p) == SUSPICIOUS

    def test_suspicious_newbie_first_purchase(self):
        # The newbie chancer: account 0 months, first purchase.
        p = _profile(account_age_months=0, is_first_purchase=True)
        assert assess_genuineness(p) == SUSPICIOUS

    def test_suspicious_young_account(self):
        p = _profile(account_age_months=2)
        assert assess_genuineness(p) == SUSPICIOUS

    def test_suspicious_smaller_burst(self):
        p = _profile(complaints_last_30_days=3)
        assert assess_genuineness(p) == SUSPICIOUS

    def test_abuser_precedence_over_suspicious(self):
        # A profile tripping both abuse and suspicion signals is the worse one.
        p = _profile(refund_to_order_ratio=0.9, account_age_months=0,
                     is_first_purchase=True)
        assert assess_genuineness(p) == LIKELY_ABUSER


# ---------------------------------------------------------------------------
# Check 2 — the three claim states + the CONTRADICTED note bank
# ---------------------------------------------------------------------------

class TestClaimVerification:
    def test_confirmed_by_logged_flag(self):
        assert verify_claim(_profile(prior_promise_logged=True)) == CONFIRMED

    def test_confirmed_by_affirming_note(self):
        notes = "Customer was assured replacement on last contact."
        assert verify_claim(_profile(customer_care_notes=notes)) == CONFIRMED

    def test_confirmed_by_coupon_promise_note(self):
        notes = "Agent promised 20% coupon on previous call, not yet issued."
        assert verify_claim(_profile(customer_care_notes=notes)) == CONFIRMED

    @pytest.mark.parametrize("notes", [
        "Informed customer no refund applicable per policy; customer agreed.",
        "Explained item is non-returnable (perishable); customer acknowledged.",
        "Clarified no prior promise was made; resolved on call.",
    ])
    def test_contradicted_note_bank(self, notes):
        # A denying note exists only when a prior contact actually happened.
        p = _profile(customer_care_notes=notes, prior_contacts_this_issue=1)
        assert verify_claim(p) == CONTRADICTED

    def test_unverified_when_records_silent(self):
        # Message may claim "your rep promised a refund"; our records show none.
        assert verify_claim(_profile(customer_care_notes="")) == UNVERIFIED

    def test_denying_note_without_prior_contact_is_unverified(self):
        # Guard: a denial with zero logged contacts is not a verifiable record.
        p = _profile(customer_care_notes="no refund applicable",
                     prior_contacts_this_issue=0)
        assert verify_claim(p) == UNVERIFIED

    def test_logged_promise_confirms_even_if_contacts_zero(self):
        # A logged promise is authoritative; it proves an interaction occurred.
        p = _profile(prior_promise_logged=True, prior_contacts_this_issue=0)
        assert verify_claim(p) == CONFIRMED

    def test_logged_flag_outranks_denying_note(self):
        # Explicit logged promise wins over ambiguous note phrasing.
        p = _profile(prior_promise_logged=True,
                     customer_care_notes="non-returnable item")
        assert verify_claim(p) == CONFIRMED


# ---------------------------------------------------------------------------
# Tone-blindness (Rule 6) and the contract shape
# ---------------------------------------------------------------------------

class TestContract:
    _REQUIRED = {"genuineness", "claim_status", "reason"}

    def test_output_has_all_required_keys(self):
        out = investigate(_FURIOUS, _profile())
        assert self._REQUIRED <= set(out)

    def test_required_values_are_plain_str(self):
        out = investigate(_FURIOUS, _profile())
        assert all(isinstance(out[k], str) for k in self._REQUIRED)

    def test_optional_diagnostic_keys_present_and_typed(self):
        out = investigate(_FURIOUS, _profile())
        assert isinstance(out["signals"], dict)
        assert isinstance(out["flags"], list)
        assert isinstance(out["confidence"], float)
        assert 0.0 <= out["confidence"] <= 1.0

    def test_output_is_json_serialisable(self):
        import json
        json.dumps(investigate(_FURIOUS, _profile()))  # must not raise

    def test_output_enums_are_valid(self):
        out = investigate(_FURIOUS, _profile())
        assert out["genuineness"] in GENUINENESS_VALUES
        assert out["claim_status"] in CLAIM_STATUS_VALUES

    def test_tone_does_not_change_verdict(self):
        # Same history, opposite tones -> identical trust verdict.
        p = _profile()
        assert investigate(_FURIOUS, p)["genuineness"] == \
               investigate(_CALM, p)["genuineness"] == GENUINE

    def test_furious_abuser_still_abuser(self):
        p = _profile(refund_to_order_ratio=0.83, items_kept_after_refund=3)
        assert investigate(_FURIOUS, p)["genuineness"] == LIKELY_ABUSER

    def test_does_not_raise_on_sparse_profile(self):
        # Robust to missing optional fields. A profile with no history defaults
        # age to 0, which correctly reads as untrusted (SUSPICIOUS) rather than
        # crashing — the point of this test is that it never raises.
        out = investigate(_FURIOUS, {"customer_id": "CX"})
        assert out["genuineness"] in GENUINENESS_VALUES
        assert out["claim_status"] in CLAIM_STATUS_VALUES


# ---------------------------------------------------------------------------
# C0006 — abuser with a logged promise (Trap 2)
# ---------------------------------------------------------------------------

def test_c0006_abuser_with_confirmed_promise():
    profile = lookup_profile("C0006")
    out = investigate(_FURIOUS, profile)
    assert out["genuineness"] == LIKELY_ABUSER
    assert out["claim_status"] == CONFIRMED


# ---------------------------------------------------------------------------
# _archetype quarantine (Rule 11 / Trap 1)
# ---------------------------------------------------------------------------

def test_archetype_never_in_profile():
    assert "_archetype" not in lookup_profile("C0001")


def test_module_never_uses_archetype_as_a_field():
    # The integration safety rail (Plan §6, Trap 1): the quarantined label must
    # never be read as a feature. We forbid it appearing as a string literal
    # used for lookup — e.g. profile['_archetype'] or .get('_archetype') — while
    # allowing the word in explanatory prose.
    src = (_ROOT / "backend" / "modules" / "investigator" / "investigator.py").read_text()
    forbidden = ['"_archetype"', "'_archetype'", "._archetype"]
    hits = [f for f in forbidden if f in src]
    assert not hits, f"module references quarantined label as a field: {hits}"


# ---------------------------------------------------------------------------
# Score the Investigator against the ground truth (expect ~218/220)
# ---------------------------------------------------------------------------

def test_genuineness_matches_archetype_on_real_data():
    raw = pd.read_csv(_CUSTOMERS_CSV)  # test code is the ONLY place _archetype is read
    correct = 0
    for _, row in raw.iterrows():
        profile = {k: v for k, v in row.items() if k != "_archetype"}
        if assess_genuineness(profile) == row["_archetype"]:
            correct += 1
    # The two documented near-misses (C0059, C0162) are the only allowed misses.
    assert correct >= 218, f"only {correct}/{len(raw)} matched archetype"


def test_claim_distribution_matches_plan_on_real_data():
    raw = pd.read_csv(_CUSTOMERS_CSV)
    counts = {CONFIRMED: 0, CONTRADICTED: 0, UNVERIFIED: 0}
    for _, row in raw.iterrows():
        profile = {k: v for k, v in row.items() if k != "_archetype"}
        counts[verify_claim(profile)] += 1
    assert counts == {CONFIRMED: 33, CONTRADICTED: 36, UNVERIFIED: 151}


# ---------------------------------------------------------------------------
# The professor's edge case + hardening (negation, history, robustness, reason)
# ---------------------------------------------------------------------------

class TestProfessorEdgeCase:
    """'A fraud who called 4 times and claims a promise he never got.'"""

    def test_fraud_called_4x_claim_denied_by_record(self):
        # Our notes show we DENIED the remedy -> CONTRADICTED, no payout.
        p = _profile(refund_to_order_ratio=0.83, items_kept_after_refund=3,
                     complaints_last_30_days=4, prior_contacts_this_issue=4,
                     prior_promise_logged=False,
                     customer_care_notes="Explained item is non-returnable; "
                                         "customer acknowledged.")
        out = investigate(_FURIOUS, p)
        assert out["genuineness"] == LIKELY_ABUSER
        assert out["claim_status"] == CONTRADICTED
        assert "CONTRADICTED" in out["reason"] and "4" in out["reason"]

    def test_fraud_called_4x_no_record_at_all(self):
        # No note, but he asserts a promise. His word is not our record.
        p = _profile(refund_to_order_ratio=0.83, items_kept_after_refund=3,
                     complaints_last_30_days=4, prior_contacts_this_issue=4,
                     prior_promise_logged=False, customer_care_notes="")
        out = investigate(_FURIOUS, p)
        assert out["genuineness"] == LIKELY_ABUSER
        assert out["claim_status"] == UNVERIFIED

    def test_fraud_with_genuinely_logged_promise_is_confirmed_but_flagged(self):
        # Honour-capped conflict (Plan §4.7): CONFIRMED, but abuse is flagged.
        p = _profile(refund_to_order_ratio=0.58, items_kept_after_refund=4,
                     complaints_last_30_days=4, prior_contacts_this_issue=2,
                     prior_promise_logged=True,
                     customer_care_notes="Customer was assured replacement.")
        out = investigate(_FURIOUS, p)
        assert out["genuineness"] == LIKELY_ABUSER
        assert out["claim_status"] == CONFIRMED
        assert "PROMISE_TO_ABUSER" in out["flags"]


class TestSemanticNoteReading:
    """Negation-aware reading of the agent NOTES (Module 2's real NLP task)."""

    @pytest.mark.parametrize("note", [
        "Clarified no promise was ever made to the customer.",
        "Agent did not promise any refund on the call.",
        "Customer was never promised a replacement.",
    ])
    def test_negated_promise_is_not_confirmed(self, note):
        p = _profile(customer_care_notes=note, prior_contacts_this_issue=1)
        assert verify_claim(p) != CONFIRMED

    def test_real_affirming_note_still_confirms(self):
        p = _profile(customer_care_notes="Agent promised a full refund.",
                     prior_contacts_this_issue=1)
        assert verify_claim(p) == CONFIRMED


class TestConversationHistory:
    """Optional, backward-compatible chat-memory awareness."""

    def test_no_history_arg_keeps_old_behaviour(self):
        p = _profile()
        assert investigate(_FURIOUS, p) == investigate(_FURIOUS, p, None)

    def test_resolved_claim_is_reused_not_reasked(self):
        # Profile alone would be UNVERIFIED, but the chat already settled it.
        p = _profile(prior_contacts_this_issue=0)
        out = investigate(_FURIOUS, p,
                          conversation_history=[{"claim_status": CONFIRMED}])
        assert out["claim_status"] == CONFIRMED
        assert "earlier" in out["reason"].lower()

    def test_latest_history_resolution_wins(self):
        p = _profile()
        hist = [{"claim_status": UNVERIFIED}, {"claim_status": CONTRADICTED}]
        assert investigate(_FURIOUS, p, hist)["claim_status"] == CONTRADICTED

    def test_malformed_history_is_ignored(self):
        p = _profile()
        for bad in ([None], ["string"], [{"foo": "bar"}], []):
            out = investigate(_FURIOUS, p, bad)
            assert out["claim_status"] in CLAIM_STATUS_VALUES


class TestRobustness:
    """Never crash on junk; always return a valid, reasoned verdict."""

    @pytest.mark.parametrize("profile", [
        {}, None, {"customer_id": "X"},
        {"refund_to_order_ratio": None, "account_age_months": None},
        {"refund_to_order_ratio": "abc", "complaints_last_30_days": ""},
        {"refund_to_order_ratio": float("nan")},
        {"is_first_purchase": "true", "prior_promise_logged": "False"},
    ])
    def test_never_raises_and_reason_always_present(self, profile):
        out = investigate(_FURIOUS, profile)
        assert out["genuineness"] in GENUINENESS_VALUES
        assert out["claim_status"] in CLAIM_STATUS_VALUES
        assert isinstance(out["reason"], str) and len(out["reason"]) > 10

    def test_reason_is_specific_for_every_genuineness(self):
        # Each verdict gets a reason that names its own verdict word.
        cases = {
            GENUINE: _profile(),
            SUSPICIOUS: _profile(account_age_months=0, is_first_purchase=True),
            LIKELY_ABUSER: _profile(refund_to_order_ratio=0.9),
        }
        for verdict, prof in cases.items():
            assert verdict in investigate(_FURIOUS, prof)["reason"]

    def test_reason_matches_returned_claim_status(self):
        # The reason text must never describe a different claim_status than the
        # one actually returned (history-override consistency).
        p = _profile(prior_contacts_this_issue=0)
        out = investigate(_FURIOUS, p,
                          conversation_history=[{"claim_status": CONFIRMED}])
        assert out["claim_status"] == CONFIRMED
        assert "CONFIRMED" in out["reason"]
        assert "UNVERIFIED" not in out["reason"]

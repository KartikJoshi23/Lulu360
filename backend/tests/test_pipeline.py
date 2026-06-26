"""
test_pipeline.py — Module 4 integration tests (Implementation Plan Sec.8).

Runs the full stitched pipeline offline/deterministically (FLAN-T5 disabled,
audit + resolutions logs pointed at temp files BEFORE imports). Asserts the
consolidated contract, JSON-safety, the central email rule, and 404 behaviour.

    cd <repo> && python -m pytest backend/tests/test_pipeline.py -q
"""

import json
import os
import sys
import tempfile

os.environ["LULU_DISABLE_FLAN"] = "1"
_TMP = tempfile.gettempdir()
os.environ["LULU_AUDIT_LOG"] = os.path.join(_TMP, "lulu_pipe_audit.jsonl")
os.environ["LULU_RESOLUTIONS_LOG"] = os.path.join(_TMP, "lulu_pipe_resolutions.jsonl")
for _f in (os.environ["LULU_AUDIT_LOG"], os.environ["LULU_RESOLUTIONS_LOG"]):
    if os.path.exists(_f):
        os.remove(_f)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest  # noqa: E402

from backend.pipeline import resolve            # noqa: E402
from backend import stats                       # noqa: E402
from shared.enums import EMAIL_ACTIONS, ACTIONS, REFUND_TYPES  # noqa: E402

_TOP_KEYS = {"customer_id", "message", "reader", "investigator", "economist",
             "voice", "email_fired", "audit_id", "automation"}


def test_resolve_returns_full_contract():
    r = resolve("The item arrived damaged and cracked.", "C0018")
    assert _TOP_KEYS <= set(r)
    assert set(r["reader"]) >= {"issue_type", "frustration", "confidence"}
    assert set(r["investigator"]) >= {"genuineness", "claim_status", "reason"}
    assert set(r["economist"]) == {"action", "refund_type", "coupon_percent",
                                   "wallet_credit", "escalate", "email_trigger", "reason"}
    assert "reply_text" in r["voice"]


def test_response_is_json_serialisable():
    r = resolve("I was charged twice for one order.", "C0005")
    json.dumps(r)  # must not raise -> no NumPy leaks across the boundary


def test_economist_enum_membership():
    r = resolve("My delivery never arrived.", "C0001")
    assert r["economist"]["action"] in ACTIONS
    assert r["economist"]["refund_type"] in REFUND_TYPES


def test_email_rule_holds_end_to_end():
    # email_fired must agree with the action's membership in EMAIL_ACTIONS.
    for cid in ("C0018", "C0001", "C0016", "C0020"):
        r = resolve("My product is broken and defective.", cid)
        action = r["economist"]["action"]
        assert r["email_fired"] == (action in EMAIL_ACTIONS)
        if action not in EMAIL_ACTIONS:
            assert r["voice"]["email"] is None
            assert r["audit_id"] is None


def test_general_query_gets_service_reply_not_compensation_refusal():
    r = resolve("Hello Lulu, do you deliver to my area. Appreciate it.", "C0007")
    assert r["reader"]["issue_type"] == "General_Query"
    assert r["economist"]["action"] == "ACKNOWLEDGE"
    assert r["email_fired"] is False
    reply = r["voice"]["reply_text"].lower()
    assert "delivery availability" in reply
    assert "area" in reply
    assert "compensation" not in reply
    assert "refund" not in reply


def test_unknown_customer_raises_keyerror():
    with pytest.raises(KeyError):
        resolve("hello", "C9999")


def test_stats_track_resolutions():
    # A fresh resolutions log accumulates rows and yields a sane automation rate.
    if os.path.exists(os.environ["LULU_RESOLUTIONS_LOG"]):
        os.remove(os.environ["LULU_RESOLUTIONS_LOG"])
    for cid in ("C0018", "C0001", "C0020"):
        stats.record_resolution(resolve("broken defective item", cid))
    s = stats.compute_stats()
    assert s["total"] == 3
    assert 0.0 <= s["automation_rate"] <= 1.0
    assert sum(s["by_action"].values()) == 3

"""
test_voice.py - Module 4 required tests (Plan 8.1).

Run offline/deterministically through the template path by disabling FLAN-T5
and pointing the audit log at a temp file BEFORE importing voice.

    cd lulucare360 && python -m pytest backend/tests/test_voice.py -v
"""

import json
import os
import sys
import tempfile

# Must be set before voice is imported (it reads these at import time).
os.environ["LULU_DISABLE_FLAN"] = "1"
_TMP_AUDIT = os.path.join(tempfile.gettempdir(), "lulu_test_audit.jsonl")
if os.path.exists(_TMP_AUDIT):
    os.remove(_TMP_AUDIT)
os.environ["LULU_AUDIT_LOG"] = _TMP_AUDIT

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from shared import enums as E                       # noqa: E402
from backend.modules.voice import voice             # noqa: E402

PROFILE = {"customer_id": "C0005"}
MESSAGE = "My order arrived damaged, please help."


def _decision(action, **over):
    d = {"action": action, "refund_type": E.NONE, "coupon_percent": 0,
         "wallet_credit": 0, "escalate": False,
         "email_trigger": action in E.EMAIL_ACTIONS}
    d.update(over)
    return d


# --- a reply is produced for every action ----------------------------------
def test_reply_for_every_action():
    for action in E.ACTIONS:
        d = _decision(action, coupon_percent=20 if action == E.COUPON else 0,
                      wallet_credit=200 if action == E.WALLET_CREDIT else 0,
                      refund_type=E.KEEP_ITEM if action == E.REFUND else E.NONE)
        reply = voice.generate_reply(d, MESSAGE)
        assert isinstance(reply, str) and len(reply) > 15


# --- email fires iff email_trigger -----------------------------------------
def test_email_iff_trigger():
    for action in E.ACTIONS:
        d = _decision(action, coupon_percent=20 if action == E.COUPON else 0,
                      wallet_credit=200 if action == E.WALLET_CREDIT else 0,
                      refund_type=E.PICKUP if action == E.REFUND else E.NONE)
        reply = voice.generate_reply(d, MESSAGE)
        email = voice.fire_email(PROFILE, d, reply)
        if d["email_trigger"]:
            assert email is not None
            assert set(email) == {"to", "subject", "body"}
            assert email["to"] == "C0005@example.com"
        else:
            assert email is None


# --- ACKNOWLEDGE and ESCALATE never email ----------------------------------
def test_acknowledge_escalate_never_email():
    for action in (E.ACKNOWLEDGE, E.ESCALATE):
        d = _decision(action)
        assert d["email_trigger"] is False
        reply = voice.generate_reply(d, MESSAGE)
        assert voice.fire_email(PROFILE, d, reply) is None


# --- an audit row is written for every money action ------------------------
def test_audit_row_per_money_action():
    if os.path.exists(_TMP_AUDIT):
        os.remove(_TMP_AUDIT)
    money = [
        _decision(E.COUPON, coupon_percent=20),
        _decision(E.REFUND, refund_type=E.PICKUP),
        _decision(E.WALLET_CREDIT, wallet_credit=150),
    ]
    for d in money:
        reply = voice.generate_reply(d, MESSAGE)
        voice.fire_email(PROFILE, d, reply)
    # non-money action must NOT add a row
    voice.fire_email(PROFILE, _decision(E.ACKNOWLEDGE),
                     voice.generate_reply(_decision(E.ACKNOWLEDGE), MESSAGE))

    rows = [json.loads(l) for l in open(_TMP_AUDIT, encoding="utf-8") if l.strip()]
    assert len(rows) == 3
    assert [r["action"] for r in rows] == [E.COUPON, E.REFUND, E.WALLET_CREDIT]
    assert [r["audit_id"] for r in rows] == ["A0001", "A0002", "A0003"]


# --- the polite refusal: courteous, promises nothing -----------------------
def test_acknowledge_promises_nothing():
    reply = voice.generate_reply(_decision(E.ACKNOWLEDGE), MESSAGE).lower()
    for word in ("refund", "coupon", "discount", "wallet credit", "reimburse"):
        assert word not in reply
    assert any(w in reply for w in ("thank", "value", "appreciate"))


# --- template fallback works when FLAN-T5 is disabled ----------------------
def test_template_fallback_active():
    assert voice._load_generator() is None      # disabled in this run
    reply = voice.generate_reply(_decision(E.REFUND, refund_type=E.KEEP_ITEM), MESSAGE)
    assert "refund" in reply.lower()

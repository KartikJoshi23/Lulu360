"""
test_batch.py — coverage for the batch-sweep / audit-detail additions:
  - reader.read_messages (batched LSTM) matches read_message exactly
  - resolve(fast=True) uses the template Voice and still obeys the email rule
  - resolve accepts a pre-computed Reader output (used by /run-all)
  - the audit row stores the original message + generated reply
  - clear_audit_log truncates the trail
  - the email rule holds across the WHOLE dataset under the fast path
  - lookup_profile is O(1)-indexed and still normalises ids

Runs offline (FLAN disabled); logs pinned to temp files before import.
"""
import os
import sys
import tempfile

os.environ["LULU_DISABLE_FLAN"] = "1"
_AUDIT = os.path.join(tempfile.gettempdir(), "lulu_batch_audit.jsonl")
_RES = os.path.join(tempfile.gettempdir(), "lulu_batch_res.jsonl")
os.environ["LULU_AUDIT_LOG"] = _AUDIT
os.environ["LULU_RESOLUTIONS_LOG"] = _RES
for _f in (_AUDIT, _RES):
    if os.path.exists(_f):
        os.remove(_f)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest  # noqa: E402

from backend.data import loader                                   # noqa: E402
from backend.data.loader import lookup_profile                    # noqa: E402
from backend.modules.reader.reader import read_message, read_messages  # noqa: E402
from backend.modules.voice import voice                           # noqa: E402
from backend.pipeline import resolve                              # noqa: E402
from shared.enums import EMAIL_ACTIONS                            # noqa: E402


@pytest.fixture(autouse=True)
def _pin_logs():
    # Re-pin before every test so a sibling suite's env change can't hijack ours.
    os.environ["LULU_AUDIT_LOG"] = _AUDIT
    os.environ["LULU_RESOLUTIONS_LOG"] = _RES
    yield


_SAMPLE = [
    "The TV arrived with a cracked screen and will not turn on.",
    "Hi there, the invoice amount is wrong. Looking forward to your reply.",
    "My delivery never arrived and it has been a week.",
    "I am furious, the laptop is defective and broken!",
    "Do you deliver to my area?",
    "The app keeps crashing when I try to checkout.",
    "I returned the product but no refund came through.",
    "The fresh produce was spoiled and the packaging was damaged.",
]


def test_read_messages_matches_single():
    batch = read_messages(_SAMPLE)
    assert len(batch) == len(_SAMPLE)
    for text, b in zip(_SAMPLE, batch):
        assert b == read_message(text), f"batch != single for {text!r}"


def test_read_messages_handles_empty_and_blank():
    out = read_messages(["", "   ", _SAMPLE[0]])
    assert out[0] == {"issue_type": "General_Query", "frustration": "Low", "confidence": 0.0}
    assert out[1] == {"issue_type": "General_Query", "frustration": "Low", "confidence": 0.0}
    assert out[2]["issue_type"] and out[2]["confidence"] > 0


def test_read_messages_empty_list():
    assert read_messages([]) == []


def test_fast_resolve_obeys_email_rule_and_is_substantive():
    r = resolve("The laptop is defective and the screen is broken.", "C0013", fast=True)
    action = r["economist"]["action"]
    assert r["email_fired"] == (action in EMAIL_ACTIONS)
    assert len(r["voice"]["reply_text"]) >= 40


def test_resolve_uses_precomputed_reader():
    # A distinctive reader must flow straight through, proving resolve does not
    # re-run the Reader when one is supplied.
    rd = {"issue_type": "Billing", "frustration": "High", "confidence": 0.99}
    r = resolve("(message text is ignored here)", "C0001", fast=True, reader=rd)
    assert r["reader"]["issue_type"] == "Billing"
    assert r["reader"]["frustration"] == "High"


def test_audit_row_stores_message_and_reply():
    voice.clear_audit_log()
    msg = "The TV arrived with a cracked screen and will not turn on."
    r = resolve(msg, "C0018", fast=True)
    assert r["email_fired"] is True
    rows = voice.read_audit_log()
    assert rows, "a money action must write an audit row"
    last = rows[-1]
    assert last["message"] == msg
    assert len(last["reply_text"]) >= 40
    assert "@" in last["email"]["to"]
    assert last["email"]["subject"] and last["email"]["body"]


def test_clear_audit_log_empties_the_trail():
    resolve("broken defective item", "C0018", fast=True)
    assert voice.read_audit_log()
    voice.clear_audit_log()
    assert voice.read_audit_log() == []


def test_email_rule_holds_across_whole_dataset_fast():
    voice.clear_audit_log()
    pairs = loader.all_messages()
    readers = read_messages([t for _, t in pairs])
    assert len(readers) == len(pairs)
    emails = money = 0
    for (cid, msg), rd in zip(pairs, readers):
        res = resolve(msg, cid, fast=True, reader=rd)
        action = res["economist"]["action"]
        money += action in EMAIL_ACTIONS
        emails += res["email_fired"]
        assert res["email_fired"] == (action in EMAIL_ACTIONS)
        assert (res["audit_id"] is not None) == (action in EMAIL_ACTIONS)
        assert len(res["voice"]["reply_text"]) >= 40
    assert emails == money
    assert len(voice.read_audit_log()) == emails


def test_lookup_profile_indexed_and_normalised():
    p = lookup_profile("C0018")
    assert p is not None and p["customer_id"] == "C0018"
    assert lookup_profile(" c0018 ") == p          # trimmed + upper-cased
    assert lookup_profile("C9999") is None          # unknown
    # native, JSON-safe types (Integration Rule 2)
    assert isinstance(p["is_perishable_or_hygiene"], bool)

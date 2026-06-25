"""
Module 1 - The Reader.  *** PLACEHOLDER - owned by the Reader sub-team. ***

This is NOT our deliverable. The Reader team replaces this file with the real
LSTM (reader_issue.keras / reader_frustration.keras). We ship a tiny
keyword stub that honours the frozen contract so the Voice team's pipeline and
API run end-to-end against realistic inputs while we build Module 4.

Contract (Plan 4.1):
    read_message(text) -> {issue_type: str, frustration: str, confidence: float}
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from shared import enums as E  # noqa: E402

_ISSUE_KEYWORDS = {
    E.ISSUE_TYPES[0]: ("deliver", "courier", "package", "shipment", "arrive"),
    E.ISSUE_TYPES[1]: ("broken", "damaged", "cracked", "defective", "faulty", "dented"),
    E.ISSUE_TYPES[2]: ("refund", "return", "money back", "sent back", "pickup"),
    E.ISSUE_TYPES[3]: ("charge", "bill", "invoice", "coupon", "payment", "deducted"),
    E.ISSUE_TYPES[4]: ("quality", "cheap", "material", "looks nothing", "build"),
    E.ISSUE_TYPES[5]: ("app", "website", "log in", "crash", "freeze", "loading", "search"),
    E.ISSUE_TYPES[6]: ("question", "timings", "address", "available", "policy", "area"),
}

_HIGH = ("furious", "unacceptable", "last straw", "done with lulu", "had enough",
         "outrageous", "never shop", "immediately", "now or")
_MED = ("annoyed", "frustrating", "disappointed", "not happy", "unhappy",
        "bothering", "needs attention", "look into", "sort this")


def predict_frustration(text: str) -> str:
    low = text.lower()
    if any(w in low for w in _HIGH):
        return "High"
    if any(w in low for w in _MED):
        return "Medium"
    return "Low"


def read_message(text: str) -> dict:
    low = (text or "").lower()
    best, score = E.ISSUE_TYPES[6], 0
    for issue, kws in _ISSUE_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in low)
        if hits > score:
            best, score = issue, hits
    # Stub confidence: higher when keywords clearly matched, lower when not.
    confidence = 0.55 if score == 0 else min(0.95, 0.6 + 0.12 * score)
    return {
        "issue_type": best,
        "frustration": predict_frustration(text),
        "confidence": round(float(confidence), 3),
    }

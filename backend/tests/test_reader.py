"""
test_reader.py — Module 1 contract tests (Implementation Plan Sec.8).

Backend-agnostic: passes whether the live Reader is the trained LSTM or the
keyword fallback (reader.ACTIVE_BACKEND). It asserts the frozen output contract,
JSON-safety, valid enum membership, and the safe empty-input fallback — not a
specific model's accuracy.

Run from the repo root:  pytest backend/tests/test_reader.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.modules.reader import reader  # noqa: E402
from shared.enums import ISSUE_TYPES, FRUSTRATION_LEVELS  # noqa: E402

read_message = reader.read_message

_SAMPLES = [
    "My delivery never arrived and I am furious!",
    "The TV screen was cracked when I opened the box",
    "I was charged twice for the same order",
    "Hi, quick question about a return",
    "asdfghjkl xyz 123",
    "a",
]


@pytest.mark.parametrize("text", _SAMPLES)
def test_contract_keys_types_and_enums(text):
    out = read_message(text)
    assert set(out.keys()) == {"issue_type", "frustration", "confidence"}
    assert isinstance(out["issue_type"], str)
    assert isinstance(out["frustration"], str)
    assert isinstance(out["confidence"], float)
    assert out["issue_type"] in ISSUE_TYPES
    assert out["frustration"] in FRUSTRATION_LEVELS
    assert 0.0 <= out["confidence"] <= 1.0


@pytest.mark.parametrize("text", _SAMPLES + ["", "   "])
def test_json_safe_no_numpy_leak(text):
    json.dumps(read_message(text))  # must not raise (catches numpy scalars)


def test_empty_input_safe_fallback():
    for blank in ("", "   ", None):
        out = read_message(blank)
        assert out == {"issue_type": "General_Query", "frustration": "Low", "confidence": 0.0}


def test_active_backend_is_declared():
    assert reader.ACTIVE_BACKEND in ("lstm", "keyword")

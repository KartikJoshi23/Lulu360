"""
Module 1 — The Reader (NLU front door).

Exposes the frozen contract function:
    read_message(text: str) -> {issue_type: str, frustration: str, confidence: float}

Hybrid loader (resilient by design):
  * If the trained LSTM artifacts exist in backend/models/ AND TensorFlow is
    importable, the real two-head LSTM (issue + frustration) is used. Train them
    once with:  python backend/modules/reader/train_reader.py
  * Otherwise the module falls back to a deterministic keyword classifier that
    honours the same contract, so the pipeline and API still run end-to-end on a
    host without the artifacts / without TensorFlow (e.g. a constrained free
    tier). This mirrors the Voice's template-fallback philosophy: a result is
    ALWAYS produced and the contract is never broken.

Use reader.ACTIVE_BACKEND to see which path is live ("lstm" or "keyword").
"""

import os
import sys
import threading

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from shared import enums as E  # noqa: E402

# FastAPI runs sync endpoints in a threadpool, so /run-all's batch predict and a
# concurrent /resolve can hit the same Keras model from two threads. Keras
# predict is not guaranteed thread-safe, so serialise inference.
_predict_lock = threading.Lock()

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")
_REQUIRED_ARTIFACTS = (
    "reader_issue.keras", "reader_frustration.keras",
    "tokenizer.json", "label_maps.json",
)

ACTIVE_BACKEND = "keyword"   # set to "lstm" if the real model loads below

# ---------------------------------------------------------------------------
# Try to load the real LSTM. Any failure -> graceful keyword fallback.
# ---------------------------------------------------------------------------
_issue_model = _frust_model = _tok = None
_id_to_issue = _id_to_frust = None
_MAXLEN = 40


def _artifacts_present() -> bool:
    return all(os.path.exists(os.path.join(_MODEL_DIR, a)) for a in _REQUIRED_ARTIFACTS)


if _artifacts_present():
    try:
        import json

        from tensorflow.keras.models import load_model
        from tensorflow.keras.preprocessing.sequence import pad_sequences
        from tensorflow.keras.preprocessing.text import tokenizer_from_json

        with open(os.path.join(_MODEL_DIR, "label_maps.json"), encoding="utf-8") as f:
            _maps = json.load(f)
        with open(os.path.join(_MODEL_DIR, "tokenizer.json"), encoding="utf-8") as f:
            _tok = tokenizer_from_json(f.read())

        _issue_model = load_model(os.path.join(_MODEL_DIR, "reader_issue.keras"))
        _frust_model = load_model(os.path.join(_MODEL_DIR, "reader_frustration.keras"))
        _MAXLEN = int(_maps["MAXLEN"])
        _id_to_issue = {int(k): v for k, v in _maps["id_to_issue"].items()}
        _id_to_frust = {int(k): v for k, v in _maps["id_to_frust"].items()}
        _pad = pad_sequences
        ACTIVE_BACKEND = "lstm"
    except Exception as exc:  # pragma: no cover - depends on host
        print(f"[reader] LSTM artifacts present but failed to load ({exc}); "
              f"using keyword fallback")
        ACTIVE_BACKEND = "keyword"


# ---------------------------------------------------------------------------
# Keyword fallback classifier (deterministic; contract-honouring)
# ---------------------------------------------------------------------------
_ISSUE_KEYWORDS = {
    E.ISSUE_TYPES[0]: ("deliver", "courier", "package", "shipment", "arrive", "late", "never came"),
    E.ISSUE_TYPES[1]: ("broken", "damaged", "cracked", "defective", "faulty", "dented", "spoiled", "shattered"),
    E.ISSUE_TYPES[2]: ("refund", "return", "money back", "sent back", "exchange"),
    E.ISSUE_TYPES[3]: ("charge", "bill", "invoice", "payment", "deducted", "double charged", "overcharged"),
    E.ISSUE_TYPES[4]: ("quality", "cheap", "material", "looks nothing", "build", "poor quality"),
    E.ISSUE_TYPES[5]: ("app", "website", "log in", "login", "crash", "freeze", "loading", "search", "checkout"),
    E.ISSUE_TYPES[6]: ("question", "timings", "address", "available", "policy", "area", "enquiry", "inquiry"),
}
_HIGH = ("furious", "unacceptable", "last straw", "done with lulu", "had enough",
         "outrageous", "never shop", "immediately", "now or", "disgusted", "ridiculous")
_MED = ("annoyed", "frustrating", "disappointed", "not happy", "unhappy",
        "bothering", "needs attention", "look into", "sort this", "please help")

_SERVICE_INQUIRY_PHRASES = (
    "do you deliver", "deliver to my area", "delivery available", "available in my area",
    "store timing", "store timings", "opening hours", "what time do you open",
    "what time are you open", "return policy", "exchange policy",
)


def _kw_frustration(text: str) -> str:
    low = text.lower()
    if any(w in low for w in _HIGH):
        return "High"
    if any(w in low for w in _MED):
        return "Medium"
    return "Low"


def _kw_read(text: str) -> dict:
    low = (text or "").lower()
    if any(phrase in low for phrase in _SERVICE_INQUIRY_PHRASES):
        return {
            "issue_type": E.ISSUE_GENERAL_QUERY,
            "frustration": _kw_frustration(text),
            "confidence": 0.82,
        }

    best, score = E.ISSUE_TYPES[6], 0
    for issue, kws in _ISSUE_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in low)
        if hits > score:
            best, score = issue, hits
    confidence = 0.55 if score == 0 else min(0.95, 0.6 + 0.12 * score)
    return {
        "issue_type": best,
        "frustration": _kw_frustration(text),
        "confidence": round(float(confidence), 3),
    }


# ---------------------------------------------------------------------------
# Public contract function
# ---------------------------------------------------------------------------
def read_message(text: str) -> dict:
    """Classify a complaint. Returns {issue_type, frustration, confidence}
    with native, JSON-safe values; never raises on empty/garbage input."""
    if not text or not text.strip():
        return {"issue_type": "General_Query", "frustration": "Low", "confidence": 0.0}

    if ACTIVE_BACKEND == "lstm":
        seq = _pad(_tok.texts_to_sequences([text]), maxlen=_MAXLEN)
        with _predict_lock:
            issue_probs = _issue_model.predict(seq, verbose=0)[0]
            frust_probs = _frust_model.predict(seq, verbose=0)[0]
        issue_idx = int(issue_probs.argmax())
        confidence = float(issue_probs[issue_idx])
        frust_idx = int(frust_probs.argmax())
        return {
            "issue_type": str(_id_to_issue[issue_idx]),
            "frustration": str(_id_to_frust[frust_idx]),
            "confidence": round(confidence, 3),
        }

    return _kw_read(text)


def read_messages(texts) -> list:
    """Batch version of read_message: ONE model.predict over the whole list, so a
    sweep of hundreds of messages runs in seconds instead of one slow call each.
    Returns reader dicts aligned to `texts`; empty/blank inputs default safely."""
    texts = list(texts)
    out: list = [None] * len(texts)

    if ACTIVE_BACKEND != "lstm":
        for i, t in enumerate(texts):
            out[i] = _kw_read(t) if (t and str(t).strip()) else \
                {"issue_type": "General_Query", "frustration": "Low", "confidence": 0.0}
        return out

    nonempty = [(i, str(t)) for i, t in enumerate(texts) if t and str(t).strip()]
    for i, t in enumerate(texts):
        if not (t and str(t).strip()):
            out[i] = {"issue_type": "General_Query", "frustration": "Low", "confidence": 0.0}

    if nonempty:
        seqs = _pad(_tok.texts_to_sequences([t for _, t in nonempty]), maxlen=_MAXLEN)
        with _predict_lock:
            issue_probs = _issue_model.predict(seqs, verbose=0)   # (N, 7)
            frust_probs = _frust_model.predict(seqs, verbose=0)   # (N, 3)
        for k, (i, _) in enumerate(nonempty):
            ii = int(issue_probs[k].argmax())
            fi = int(frust_probs[k].argmax())
            out[i] = {
                "issue_type": str(_id_to_issue[ii]),
                "frustration": str(_id_to_frust[fi]),
                "confidence": round(float(issue_probs[k][ii]), 3),
            }
    return out

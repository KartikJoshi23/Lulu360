"""
Module 4 - The Voice (NLG + the email + the audit trail).

Owns (Implementation Plan, Section 2.4 / Table 6):
    describe_action(decision)            -> internal instruction string
    generate_reply(decision, message)    -> reply_text: str
    fire_email(profile, decision, reply) -> dict | None

Plus the append-only audit log writer (logs/audit_log.jsonl), rendered as
dashboard stage 6.

The Voice is DECISION-PRESERVING (Integration Rule 7 + 8):
  * It reads `action`, the amounts, and `email_trigger`; it NEVER changes them.
  * It NEVER recomputes the email rule - it obeys decision['email_trigger'].
  * It produces customer-facing prose only; the Economist owns every number.

Generator strategy (Trap 14): FLAN-T5 writes the reply when available; a
deterministic template generator is the guaranteed fallback so a reply ALWAYS
renders and the decision is never affected by model latency/availability.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone

# --- path-robust import of the shared enum source --------------------------
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from shared import enums as E  # noqa: E402

# --- audit log location ----------------------------------------------------
# Override with the LULU_AUDIT_LOG env var (tests point this at a temp file).
_DEFAULT_AUDIT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "logs", "audit_log.jsonl")
)
AUDIT_LOG_PATH = os.environ.get("LULU_AUDIT_LOG", _DEFAULT_AUDIT)

_audit_lock = threading.Lock()


# ===========================================================================
# 1. describe_action - turn the structured decision into an instruction
# ===========================================================================
def describe_action(decision: dict) -> str:
    """Internal phrasing of what we are offering. Used as the FLAN-T5
    instruction and as the backbone of the template fallback. This is NOT the
    customer-facing reply; it never leaks to the user verbatim."""
    action = decision["action"]

    if action == E.ACKNOWLEDGE:
        return ("politely acknowledge the complaint, show empathy, and offer "
                "no compensation")
    if action == E.COUPON:
        return (f"apologise and offer a {int(decision['coupon_percent'])}% "
                f"discount coupon on the next order")
    if action == E.WALLET_CREDIT:
        return (f"apologise and offer {int(decision['wallet_credit'])} "
                f"{E.CURRENCY} in wallet credit")
    if action == E.REFUND:
        if decision.get("refund_type") == E.PICKUP:
            extra = "we will arrange a free pickup of the item"
        else:
            extra = "they may keep or dispose of the item, no return needed"
        return f"apologise and confirm a full refund; {extra}"
    if action == E.ESCALATE:
        return ("tell the customer their case is being reviewed by a "
                "specialist and offer no commitment yet")
    # Defensive default - an unknown action must still produce a safe reply.
    return "politely acknowledge the complaint and make no commitment"


# ===========================================================================
# 2. The generator: FLAN-T5 with a deterministic template fallback
# ===========================================================================
_generator = None          # cached transformers pipeline (or None if disabled)
_generator_loaded = False   # have we attempted to load it?


def _load_generator():
    """Lazily load google/flan-t5-small. Returns a callable
    gen(prompt, max_new_tokens) -> str, or None if unavailable.

    Disabled entirely when LULU_DISABLE_FLAN=1 (tests use this so they run
    offline and deterministically through the template path)."""
    global _generator, _generator_loaded
    if _generator_loaded:
        return _generator
    _generator_loaded = True
    if os.environ.get("LULU_DISABLE_FLAN") == "1":
        _generator = None
        return None
    _generator = _build_flan()
    return _generator


def _build_flan():
    """Build a FLAN-T5 text generator. Tries the handbook-style pipeline first
    (transformers 4.x), then falls back to loading the seq2seq model directly
    (transformers 5.x dropped the 'text2text-generation' pipeline task). Returns
    a callable or None.

    Model is configurable via LULU_FLAN_MODEL. Default flan-t5-base (250M) writes
    usable money-action replies for the demo; set it to google/flan-t5-small for
    a lighter footprint on a constrained free tier (the quality gate + template
    fallback then carry the weaker output)."""
    model_name = os.environ.get("LULU_FLAN_MODEL", "google/flan-t5-base")

    # Path 1: the handbook's pipeline API (works on transformers 4.x).
    try:
        from transformers import pipeline
        pipe = pipeline("text2text-generation", model=model_name)

        def _gen(prompt, max_new_tokens=120):
            return pipe(prompt, max_new_tokens=max_new_tokens, num_beams=4,
                        no_repeat_ngram_size=3, repetition_penalty=1.3)[0][
                "generated_text"].strip()
        return _gen
    except Exception as exc:
        print(f"[voice] pipeline task unavailable ({exc}); trying direct model")

    # Path 2: load the model + tokenizer directly (version-independent).
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        def _gen(prompt, max_new_tokens=120):
            ids = tok(prompt, return_tensors="pt", truncation=True).input_ids
            out = model.generate(ids, max_new_tokens=max_new_tokens,
                                 num_beams=4, no_repeat_ngram_size=3,
                                 repetition_penalty=1.3)
            return tok.decode(out[0], skip_special_tokens=True).strip()
        return _gen
    except Exception as exc:  # model missing / slow tier / no torch
        print(f"[voice] FLAN-T5 unavailable, using template fallback: {exc}")
        return None


# Words that must never appear in a polite ACKNOWLEDGE refusal: it must promise
# nothing. If FLAN-T5 drifts into offering money, we fall back to the template.
_PAYOUT_WORDS = ("refund", "coupon", "discount", "credit",
                 "compensat", "reimburse", "voucher")


def _violates_acknowledge(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in _PAYOUT_WORDS)


# For a money action the reply MUST name the remedy, or the customer is left
# guessing. Maps action -> words that prove the offer was stated.
_REMEDY_WORDS = {
    E.REFUND: ("refund",),
    E.COUPON: ("coupon", "discount", "%"),
    E.WALLET_CREDIT: ("credit", "wallet"),
}


def _is_degenerate(text: str) -> bool:
    """Detect the small-model failure mode: looping repetition like
    'I'm sorry. I'm sorry. I'm sorry.' (low unique-word ratio)."""
    words = text.lower().split()
    if len(words) < 8:
        return False
    return (len(set(words)) / len(words)) < 0.5


def _low_quality(text: str, decision: dict) -> bool:
    """True if the generated reply is not safe to send -> caller falls back to
    the deterministic template. flan-t5-small is weak, so this gate is the
    practical guarantee behind Trap 14."""
    if len(text) < 15 or _is_degenerate(text):
        return True
    action = decision["action"]
    if action == E.ACKNOWLEDGE and _violates_acknowledge(text):
        return True
    remedy = _REMEDY_WORDS.get(action)
    if remedy and not any(w in text.lower() for w in remedy):
        return True   # money action that never names the remedy
    return False


def generate_reply(decision: dict, message: str) -> str:
    """Produce the customer-facing reply for any action. Always returns a
    non-empty, courteous string."""
    gen = _load_generator()
    template = _template_reply(decision, message)

    if gen is None:
        return template

    instruction = describe_action(decision)
    # Few-shot: FLAN-T5 is tuned for short answers and goes terse/generic on a
    # bare instruction. One worked example teaches it the length, warmth, and to
    # name the remedy explicitly.
    prompt = (
        "You are a Lulu customer-support agent. Write a warm, empathetic reply "
        "of two sentences that clearly states what we are offering.\n\n"
        "Complaint: My grocery delivery was two days late.\n"
        "Offer: apologise and offer a 20% discount coupon on the next order.\n"
        "Reply: We're truly sorry your delivery arrived two days late - that is "
        "not the experience we want for you. As an apology, we've added a 20% "
        "discount coupon to your account for your next order.\n\n"
        f"Complaint: {message}\n"
        f"Offer: {instruction}.\n"
        "Reply:"
    )
    try:
        out = gen(prompt, max_new_tokens=120)
    except Exception as exc:
        print(f"[voice] generation failed, using template: {exc}")
        return template

    # Quality gate: weak/degenerate output, an ACKNOWLEDGE that leaked an offer,
    # or a money reply that never names the remedy -> fall back to the
    # guaranteed-safe template (Trap 14). Customer-facing text must be reliable.
    if _low_quality(out, decision):
        return template
    return out


def _template_reply(decision: dict, message: str) -> str:
    """Deterministic, offline reply. The contractually safe fallback and the
    text the tests assert against (run with LULU_DISABLE_FLAN=1)."""
    action = decision["action"]

    if action == E.ACKNOWLEDGE:
        # The hardest reply: courteous, non-accusatory, PROMISES NOTHING.
        return ("Thank you for reaching out and for taking the time to share "
                "this with us. We have carefully reviewed your account and the "
                "details of your request. On this occasion we are not able to "
                "issue any compensation, but your feedback has been logged and "
                "we genuinely value you as a Lulu customer. Please don't "
                "hesitate to contact us about any future order.")

    if action == E.COUPON:
        pct = int(decision["coupon_percent"])
        return (f"We're sorry for the trouble this has caused. As an apology, "
                f"we'd like to offer you a {pct}% discount coupon on your next "
                f"order. The coupon details are on their way to your email - "
                f"thank you for giving us the chance to make this right.")

    if action == E.WALLET_CREDIT:
        amt = int(decision["wallet_credit"])
        return (f"We're sorry for the inconvenience. To make up for it, we've "
                f"added {amt} {E.CURRENCY} in wallet credit to your account, "
                f"which you can use on any future purchase. A confirmation is "
                f"on its way to your email. Thank you for your patience.")

    if action == E.REFUND:
        if decision.get("refund_type") == E.PICKUP:
            extra = ("We will arrange a free pickup of the item at a time that "
                     "suits you")
        else:
            extra = ("There's no need to return the item - please keep or "
                     "dispose of it as you wish")
        return (f"We're truly sorry about this experience. We've confirmed a "
                f"full refund for your order. {extra}. A confirmation email is "
                f"on its way, and thank you for letting us put this right.")

    if action == E.ESCALATE:
        return ("Thank you for getting in touch. Your case needs a closer look, "
                "so we've passed it to a specialist on our team who will review "
                "the details and follow up with you directly. We appreciate "
                "your patience while we look into this properly.")

    return ("Thank you for contacting Lulu. We've received your message and "
            "will be in touch shortly.")


# ===========================================================================
# 3. fire_email + the append-only audit trail
# ===========================================================================
_SUBJECTS = {
    E.COUPON: "A coupon for you from Lulu",
    E.REFUND: "Your Lulu refund is confirmed",
    E.WALLET_CREDIT: "Lulu wallet credit added",
}


def _next_audit_id() -> str:
    """A0001, A0002, ... based on how many rows already exist."""
    n = 0
    if os.path.exists(AUDIT_LOG_PATH):
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as fh:
            n = sum(1 for line in fh if line.strip())
    return f"A{n + 1:04d}"


def fire_email(profile: dict, decision: dict, reply_text: str):
    """Compose and 'send' the email when (and only when) email_trigger is True,
    and write one append-only audit row for the money action.

    Returns the email dict {to, subject, body} or None. The Voice obeys
    decision['email_trigger']; it never recomputes the rule (Integration
    Rule 9). ACKNOWLEDGE and ESCALATE carry email_trigger=False -> no email,
    no audit row."""
    if not decision.get("email_trigger"):
        return None

    action = decision["action"]
    cust = str(profile["customer_id"])
    email = {
        "to": f"{cust}@example.com",
        "subject": _SUBJECTS.get(action, "An update from Lulu"),
        "body": reply_text,
    }

    record = {
        "audit_id": _next_audit_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": cust,
        "action": action,
        "refund_type": decision.get("refund_type", E.NONE),
        "coupon_percent": int(decision.get("coupon_percent", 0)),
        "wallet_credit": int(decision.get("wallet_credit", 0)),
        "email": email,
    }

    with _audit_lock:
        # _next_audit_id is read inside the lock to keep ids monotonic under
        # concurrent requests.
        record["audit_id"] = _next_audit_id()
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    return email


def read_last_audit_id():
    """audit_id of the most recent money action, or None. Lets the pipeline
    populate the consolidated response's audit_id field."""
    if not os.path.exists(AUDIT_LOG_PATH):
        return None
    last = None
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line
    if last is None:
        return None
    try:
        return json.loads(last)["audit_id"]
    except (json.JSONDecodeError, KeyError):
        return None


def read_audit_log():
    """Whole audit trail as a list of dicts - dashboard stage 6."""
    rows = []
    if not os.path.exists(AUDIT_LOG_PATH):
        return rows
    with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows

"""
Module 4 - The Voice (NLG + the email + the audit trail).

Owns (Implementation Plan, Section 2.4 / Table 6):
    describe_action(decision)            -> internal instruction string
    generate_reply(decision, message)    -> reply_text: str
    fire_email(profile, decision, reply) -> (email_dict, audit_id) | (None, None)

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


def _audit_path() -> str:
    """Resolve the audit-log path at call time so LULU_AUDIT_LOG changes (e.g.
    set by tests) always take effect regardless of module import order."""
    return os.environ.get("LULU_AUDIT_LOG", _DEFAULT_AUDIT)

_audit_lock = threading.Lock()


# ===========================================================================
# 1. describe_action - turn the structured decision into an instruction
# ===========================================================================
def describe_action(decision: dict) -> str:
    """Internal phrasing of what we are offering. Used as the FLAN-T5
    instruction and as the backbone of the template fallback. This is NOT the
    customer-facing reply; it never leaks to the user verbatim."""
    action = decision["action"]
    reason = str(decision.get("reason", ""))

    if action == E.ACKNOWLEDGE:
        if "General_Query service inquiry" in reason:
            return ("answer the customer's service question helpfully, ask for "
                    "any missing details, and do not discuss compensation")
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
    reason = str(decision.get("reason", ""))

    if action == E.ACKNOWLEDGE:
        if "General_Query service inquiry" in reason:
            return _inquiry_reply(message)
        # The hardest reply: courteous, non-accusatory, PROMISES NOTHING.
        return ("Thank you for reaching out and sharing this with us. We have "
                "reviewed the details available on your account and logged your "
                "feedback for our care team. We are unable to apply a remedy on "
                "this request, but we appreciate you giving Lulu the chance to "
                "review it and support you better next time.")

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


def _inquiry_reply(message: str) -> str:
    """Helpful service response for General_Query messages, without entering
    the compensation/refund policy path."""
    low = (message or "").lower()
    if "deliver" in low or "delivery" in low or "area" in low:
        return ("Thank you for contacting Lulu. We can help you check delivery "
                "availability for your area. Please share your area name, full "
                "delivery address, or nearest landmark, and our team will "
                "confirm whether delivery is currently available there.")
    if "time" in low or "timing" in low or "hours" in low or "open" in low:
        return ("Thank you for contacting Lulu. Store and service timings can "
                "vary by location, so please share the branch or area you are "
                "asking about and we will confirm the latest hours for you.")
    if "return" in low or "policy" in low or "exchange" in low:
        return ("Thank you for contacting Lulu. We can guide you on the right "
                "return or exchange process. Please share the order details and "
                "product category so we can confirm the applicable policy.")
    return ("Thank you for contacting Lulu. We can help with that request. "
            "Please share the relevant order, branch, or area details and our "
            "care team will guide you with the next step.")


# ===========================================================================
# 3. fire_email + the append-only audit trail
# ===========================================================================
# Sign-off used on every customer email.
_SIGNATURE = (
    "Warm regards,\n"
    "The LuluCare Team\n"
    "Lulu Hypermarket · Customer Experience"
)


def _compose_subject(decision: dict, audit_id: str) -> str:
    """A specific, informative subject line per money action."""
    action = decision["action"]
    if action == E.REFUND:
        return f"Your Lulu refund is confirmed (ref {audit_id})"
    if action == E.COUPON:
        pct = int(decision.get("coupon_percent", 0))
        return f"A {pct}% coupon has been added to your Lulu account (ref {audit_id})"
    if action == E.WALLET_CREDIT:
        amt = int(decision.get("wallet_credit", 0))
        return f"{E.CURRENCY} {amt} wallet credit added to your Lulu account (ref {audit_id})"
    return f"An update on your Lulu order (ref {audit_id})"


def _compose_email_body(customer_id: str, decision: dict, audit_id: str) -> str:
    """A full, self-contained confirmation email: greeting, the concrete remedy
    with its timeline/next step, a reference + account line, and a sign-off.

    Deliberately NOT the short on-screen reply (which mentions 'an email is on its
    way' — odd to read inside the email itself)."""
    action = decision["action"]

    if action == E.REFUND:
        opening = (
            "We're truly sorry your order didn't meet the standard you rightly "
            "expect from Lulu. We've approved a full refund, which will appear on "
            "your original payment method within 5–7 business days."
        )
        if decision.get("refund_type") == E.PICKUP:
            next_step = (
                "Our courier will collect the item from you within 2 business days, "
                "at a time that suits you — there's nothing you need to prepare."
            )
        else:
            next_step = (
                "You're welcome to keep or dispose of the item — there's no need to "
                "return it to us."
            )
    elif action == E.COUPON:
        pct = int(decision.get("coupon_percent", 0))
        opening = (
            "We're sorry for the inconvenience this caused. As a gesture of "
            f"goodwill, we've added a {pct}% discount coupon to your Lulu account."
        )
        next_step = (
            "It's valid on your next order for the next 30 days and will be applied "
            "automatically at checkout."
        )
    elif action == E.WALLET_CREDIT:
        amt = int(decision.get("wallet_credit", 0))
        opening = (
            "We're sorry for the trouble this caused. To make things right, we've "
            f"added {E.CURRENCY} {amt} in wallet credit to your Lulu account."
        )
        next_step = "Your credit is ready to use on any future purchase and never expires."
    else:
        opening = "Here is an update on your recent Lulu order."
        next_step = ""

    lines = ["Dear valued Lulu customer,", "", opening]
    if next_step:
        lines += ["", next_step]
    lines += [
        "",
        f"Reference: {audit_id}     Account: {customer_id}",
        "",
        "If anything isn't quite right, simply reply to this email and our care "
        "team will personally look into it.",
        "",
        _SIGNATURE,
    ]
    return "\n".join(lines)


def _next_audit_id() -> str:
    """A0001, A0002, ... based on how many rows already exist."""
    n = 0
    path = _audit_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            n = sum(1 for line in fh if line.strip())
    return f"A{n + 1:04d}"


def fire_email(profile: dict, decision: dict, reply_text: str = ""):
    """Compose and 'send' the confirmation email when (and only when)
    email_trigger is True, and write one append-only audit row.

    Returns (email_dict, audit_id) or (None, None).  The audit_id is assigned
    inside the lock so it is always correct even under concurrent requests, and
    returned directly so callers never need to re-read the log to find it.

    The Voice obeys decision['email_trigger']; it never recomputes the rule
    (Integration Rule 9). ACKNOWLEDGE and ESCALATE carry email_trigger=False
    → no email, no audit row."""
    if not decision.get("email_trigger"):
        return None, None

    action = decision["action"]
    cust = str(profile["customer_id"])

    with _audit_lock:
        # audit_id is assigned inside the lock so ids stay monotonic under
        # concurrent requests AND the email can quote it as its reference.
        audit_id = _next_audit_id()
        email = {
            "to": f"{cust}@example.com",
            "subject": _compose_subject(decision, audit_id),
            "body": _compose_email_body(cust, decision, audit_id),
        }
        record = {
            "audit_id": audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "customer_id": cust,
            "action": action,
            "refund_type": decision.get("refund_type", E.NONE),
            "coupon_percent": int(decision.get("coupon_percent", 0)),
            "wallet_credit": int(decision.get("wallet_credit", 0)),
            "email": email,
        }
        path = _audit_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    return email, audit_id


def read_audit_log():
    """Whole audit trail as a list of dicts - dashboard stage 6."""
    rows = []
    path = _audit_path()
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip a corrupt/partial row rather than 500 /audit
    return rows

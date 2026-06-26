"""
shared/schemas.py — Pydantic models for every interface contract (Plan §3, §4).

One source of truth for the request/response shapes that cross the API boundary.
The FastAPI app (backend/api/main.py) imports these so the OpenAPI docs and the
React contract stay in lock-step with the frozen contracts in shared/contracts.md.
"""

from typing import Optional

from pydantic import BaseModel


# --- request ---------------------------------------------------------------
class ResolveRequest(BaseModel):
    message: str
    customer_id: str


# --- per-module outputs (Plan §4.1–4.4) ------------------------------------
class ReaderOut(BaseModel):
    issue_type: str
    frustration: str
    confidence: float


class InvestigatorOut(BaseModel):
    genuineness: str
    claim_status: str
    reason: str
    # optional, additive diagnostics (downstream may ignore)
    signals: Optional[dict] = None
    flags: Optional[list] = None
    confidence: Optional[float] = None


class EconomistOut(BaseModel):
    action: str
    refund_type: str
    coupon_percent: int
    wallet_credit: int
    escalate: bool
    email_trigger: bool
    reason: str


class EmailOut(BaseModel):
    to: str
    subject: str
    body: str


class VoiceOut(BaseModel):
    reply_text: str
    email: Optional[EmailOut] = None


class AutomationOut(BaseModel):
    escalated: bool


# --- consolidated pipeline response (Plan §4.5) ----------------------------
class ResolveResponse(BaseModel):
    customer_id: str
    message: str
    reader: ReaderOut
    investigator: InvestigatorOut
    economist: EconomistOut
    voice: VoiceOut
    email_fired: bool
    audit_id: Optional[str] = None
    automation: AutomationOut


# --- auxiliary endpoints ---------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    reader_backend: str   # "lstm" | "keyword"
    flan_enabled: bool


class StatsResponse(BaseModel):
    total: int
    escalated: int
    emails_sent: int
    automation_rate: float
    by_action: dict

"""
backend/api/main.py - the single FastAPI service (Plan 1.2, 7.3).

Hosted OFF Netlify (Render/Railway/HF Spaces). Netlify serves only the React
bundle, which POSTs here. Endpoints:

    POST /resolve  {message, customer_id} -> consolidated response (Plan 4.5)
    GET  /health                          -> {status: "ok"}
    GET  /audit                           -> the audit trail (dashboard stage 6)

CORS is enabled for the Netlify origin + localhost; without it the browser
blocks every cross-origin request and the dashboard shows empty panels.
"""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI, HTTPException                 # noqa: E402
from fastapi.middleware.cors import CORSMiddleware         # noqa: E402
from pydantic import BaseModel                             # noqa: E402

from backend.pipeline import resolve                       # noqa: E402
from backend.modules.voice import voice                    # noqa: E402

app = FastAPI(title="LuluCare 360 API", version="1.0")

# Allowed origins: the deployed Netlify site (via env) + local dev.
_origins = [
    os.environ.get("NETLIFY_ORIGIN", "https://lulucare360.netlify.app"),
    "http://localhost:5173",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ResolveRequest(BaseModel):
    message: str
    customer_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/resolve")
def resolve_endpoint(req: ResolveRequest):
    try:
        return resolve(req.message, req.customer_id)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=f"Unknown customer_id: {req.customer_id}")


@app.get("/audit")
def audit():
    return {"audit_log": voice.read_audit_log()}

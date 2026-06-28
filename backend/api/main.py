"""
backend/api/main.py — the single FastAPI service (Plan 1.2, 7.3).

Hosted OFF Netlify (Render/Railway/HF Spaces). Netlify serves only the React
bundle, which POSTs here. Endpoints:

    POST /resolve  {message, customer_id} -> consolidated pipeline response
    GET  /health                          -> {status, reader_backend, flan_enabled}
    GET  /audit                           -> the money-action audit trail
    GET  /stats                           -> automation rate + action breakdown

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

from backend import stats                                  # noqa: E402
from backend.data import loader                            # noqa: E402
from backend.pipeline import resolve                       # noqa: E402
from backend.modules.reader import reader                  # noqa: E402
from backend.modules.voice import voice                    # noqa: E402
from shared.schemas import (                               # noqa: E402
    ResolveRequest, ResolveResponse, HealthResponse, StatsResponse,
    CustomerCatalogEntry,
)

app = FastAPI(title="LuluCare 360 API", version="1.0")

# Allowed origins: the deployed frontend (via env) + local dev. FRONTEND_ORIGIN
# is the generic name; NETLIFY_ORIGIN is still honoured for backwards
# compatibility. Any extra comma-separated origins can be added via
# EXTRA_CORS_ORIGINS.
_explicit = os.environ.get("FRONTEND_ORIGIN") or os.environ.get(
    "NETLIFY_ORIGIN", "https://lulucare360.netlify.app")
_origins = [
    _explicit,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_origins += [o.strip() for o in os.environ.get("EXTRA_CORS_ORIGINS", "").split(",") if o.strip()]

# The frontend is built and deployed on Vercel (see vercel.json), which serves
# production and per-deploy preview URLs under *.vercel.app — and *.netlify.app
# if hosted there. A regex covers those without pinning the exact subdomain, so
# the live dashboard isn't silently blocked by CORS after a redeploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://([a-z0-9-]+\.)*(vercel\.app|netlify\.app)",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Contract models live in shared/schemas.py (imported above) so the OpenAPI docs
# and the React contract stay in lock-step with shared/contracts.md.


# ===========================================================================
# Endpoints
# ===========================================================================
@app.get("/health", response_model=HealthResponse)
def health():
    return {
        "status": "ok",
        "reader_backend": reader.ACTIVE_BACKEND,                       # "lstm" | "keyword"
        "flan_enabled": os.environ.get("LULU_DISABLE_FLAN") != "1",
    }


@app.post("/resolve", response_model=ResolveResponse)
def resolve_endpoint(req: ResolveRequest):
    try:
        result = resolve(req.message, req.customer_id)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=f"Unknown customer_id: {req.customer_id}")
    # Telemetry for the automation-rate stats card (best-effort; never blocks).
    try:
        stats.record_resolution(result)
    except Exception:  # pragma: no cover - logging must not break the response
        pass
    return result


@app.get("/customers", response_model=list[CustomerCatalogEntry])
def customers():
    """The customer + message catalog for the dashboard picker: every customer
    who has complaints, with their tier and their real messages."""
    return loader.message_catalog()


@app.get("/audit")
def audit():
    return {"audit_log": voice.read_audit_log()}


@app.get("/stats", response_model=StatsResponse)
def stats_endpoint():
    return stats.compute_stats()

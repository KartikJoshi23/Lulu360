"""
backend/stats.py — lightweight resolution telemetry for the dashboard.

The audit log (voice.py) only records *money* actions. To compute the
automation rate we need EVERY resolution (including ACKNOWLEDGE / ESCALATE), so
this module keeps a separate append-only log and derives the stats card numbers.

    automation_rate = 1 - escalated / total      (target >= 0.90)

JSON-safe and dependency-free. The log path is overridable via
LULU_RESOLUTIONS_LOG (tests point it at a temp file).
"""

import json
import os
import threading
from datetime import datetime, timezone

_DEFAULT_LOG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "logs", "resolutions.jsonl")
)


def _resolutions_log() -> str:
    """Resolve the log path at call time so LULU_RESOLUTIONS_LOG changes (e.g.
    set by tests) take effect regardless of module import order — mirrors
    voice._audit_path()."""
    return os.environ.get("LULU_RESOLUTIONS_LOG", _DEFAULT_LOG)

_lock = threading.Lock()


def record_resolution(result: dict) -> None:
    """Append one compact row describing a completed resolution."""
    econ = result.get("economist", {})
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": result.get("customer_id"),
        "action": econ.get("action"),
        "escalate": bool(econ.get("escalate", False)),
        "email_fired": bool(result.get("email_fired", False)),
    }
    path = _resolutions_log()
    with _lock:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")


def _read_rows() -> list:
    path = _resolutions_log()
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def compute_stats() -> dict:
    """Aggregate the resolutions log into the dashboard stats payload."""
    rows = _read_rows()
    total = len(rows)
    escalated = sum(1 for r in rows if r.get("escalate"))
    emails = sum(1 for r in rows if r.get("email_fired"))

    by_action: dict = {}
    for r in rows:
        a = r.get("action") or "UNKNOWN"
        by_action[a] = by_action.get(a, 0) + 1

    automation_rate = round((total - escalated) / total, 4) if total else 0.0
    return {
        "total": int(total),
        "escalated": int(escalated),
        "emails_sent": int(emails),
        "automation_rate": float(automation_rate),
        "by_action": {k: int(v) for k, v in sorted(by_action.items())},
    }

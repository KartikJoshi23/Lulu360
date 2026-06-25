"""
profile_loader — the single customer-profile lookup (Implementation Plan Sec.5,
Rule 4: "All lookups by customer_id. Profiles are fetched through a single
lookup_profile(customer_id); no module re-reads CSVs independently.").

This loader is provided by the Investigator sub-team so Module 2 is testable in
isolation. At integration time the Voice/pipeline owner may centralise an
equivalent loader; the contract is the function signature and the guarantee
that _archetype is dropped (Plan Sec.5, Rule 11 / Sec.6, Trap 1).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

# Resolve backend/data/customers.csv relative to this file.
_DATA = Path(__file__).resolve().parents[2] / "data" / "customers.csv"

# Quarantined ground-truth label: dropped at load, usable only by test code to
# score the Investigator. Never a feature, never in a response.
_QUARANTINE_COLUMNS = ["_archetype"]


@lru_cache(maxsize=1)
def _load_table() -> pd.DataFrame:
    """Read customers.csv once, dropping the leakage column on load."""
    df = pd.read_csv(_DATA).drop(columns=_QUARANTINE_COLUMNS, errors="ignore")
    return df.set_index("customer_id", drop=False)


def lookup_profile(customer_id: str) -> dict:
    """
    Return one customer's profile as a JSON-safe dict (Plan Sec.5: no NumPy
    scalars leak across boundaries). Raises KeyError if the id is unknown.

    _archetype is guaranteed absent from the returned dict.
    """
    df = _load_table()
    if customer_id not in df.index:
        raise KeyError(f"unknown customer_id: {customer_id!r}")
    row = df.loc[customer_id]
    return {k: _json_safe(v) for k, v in row.to_dict().items()}


def _json_safe(value):
    """Cast pandas/NumPy scalars to native Python types for clean serialization."""
    # pandas NA / NaN -> None
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    # NumPy scalars expose .item(); native types are returned unchanged.
    item = getattr(value, "item", None)
    return item() if callable(item) else value

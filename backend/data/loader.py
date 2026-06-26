"""
backend/data/loader.py - the single customer lookup everyone uses.

Integration Rule 4: all profile lookups go through lookup_profile(customer_id);
no module re-reads the CSV independently.

Trap 1 (ground-truth leakage): _archetype is DROPPED here on load and never
leaves this module. It is the answer column; any code that reads it would score
100% and learn nothing. Tests load it separately to score the Investigator.
"""

import os
import pandas as pd

_DATA_DIR = os.path.dirname(__file__)
_CUSTOMERS_CSV = os.path.join(_DATA_DIR, "customers.csv")

_customers = None


def _load():
    global _customers
    if _customers is None:
        df = pd.read_csv(_CUSTOMERS_CSV)
        # Trap 1: quarantine the ground-truth label at load.
        df = df.drop(columns=["_archetype"], errors="ignore")
        _customers = df
    return _customers


def lookup_profile(customer_id: str):
    """Return one customer row as a JSON-safe dict, or None if unknown.
    NumPy scalars are cast to native Python types (Integration Rule 2).

    The id is normalised (trimmed + upper-cased) so 'c0018' or ' C0018 ' resolve
    the same as 'C0018' — the canonical form in customers.csv."""
    if customer_id is None:
        return None
    cid = str(customer_id).strip().upper()
    df = _load()
    row = df[df.customer_id == cid]
    if len(row) == 0:
        return None
    raw = row.iloc[0].to_dict()
    return {k: _py(v) for k, v in raw.items()}


def _py(v):
    """Cast a NumPy/pandas scalar to a native Python type so nothing leaks
    across the JSON boundary (Integration Rule 2)."""
    if isinstance(v, bool):
        return v
    try:
        import numpy as np
        if isinstance(v, np.bool_):
            return bool(v)
        if isinstance(v, np.integer):
            return int(v)
        if isinstance(v, np.floating):
            return float(v)
    except ImportError:
        pass
    return v

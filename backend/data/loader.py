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
_MESSAGES_CSV = os.path.join(_DATA_DIR, "messages.csv")

_customers = None
_messages = None
_index = None   # normalised customer_id -> raw row dict, built once


def _load():
    global _customers
    if _customers is None:
        df = pd.read_csv(_CUSTOMERS_CSV)
        # Trap 1: quarantine the ground-truth label at load.
        df = df.drop(columns=["_archetype"], errors="ignore")
        _customers = df
    return _customers


def _profile_index():
    """customer_id -> raw row dict, keyed by the normalised id. Built once so
    lookup is O(1); the batch sweep does hundreds of lookups."""
    global _index
    if _index is None:
        df = _load()
        _index = {
            str(rec["customer_id"]).strip().upper(): rec
            for rec in df.to_dict("records")
        }
    return _index


def lookup_profile(customer_id: str):
    """Return one customer row as a JSON-safe dict, or None if unknown.
    NumPy scalars are cast to native Python types (Integration Rule 2).

    The id is normalised (trimmed + upper-cased) so 'c0018' or ' C0018 ' resolve
    the same as 'C0018' — the canonical form in customers.csv."""
    if customer_id is None:
        return None
    cid = str(customer_id).strip().upper()
    raw = _profile_index().get(cid)
    if raw is None:
        return None
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


def _load_messages():
    global _messages
    if _messages is None:
        _messages = pd.read_csv(_MESSAGES_CSV)
    return _messages


def all_messages():
    """Every (customer_id, text) pair in messages.csv, for the batch sweep that
    runs the whole dataset through the pipeline."""
    msgs = _load_messages()
    return [(str(r.customer_id), str(r.text))
            for r in msgs.itertuples(index=False)]


def message_catalog():
    """Every customer that has at least one complaint, with their loyalty tier
    and their real messages from messages.csv. Powers the dashboard's customer /
    message picker so an agent can select any customer and see their complaints.

    Returns a list (sorted by customer_id) of:
        {customer_id, loyalty_tier, messages: [{message_id, text,
                                                 issue_type, frustration}, ...]}
    """
    msgs = _load_messages()
    cust = _load()  # customers with _archetype already dropped
    tier_by_id = dict(zip(cust.customer_id, cust.loyalty_tier))

    catalog = []
    for cid, grp in msgs.groupby("customer_id", sort=True):
        catalog.append({
            "customer_id": str(cid),
            "loyalty_tier": str(tier_by_id.get(cid, "")),
            "messages": [
                {
                    "message_id": str(r.message_id),
                    "text": str(r.text),
                    "issue_type": str(r.issue_type),
                    "frustration": str(r.frustration),
                }
                for r in grp.itertuples(index=False)
            ],
        })
    return catalog

# `dataset/` — the provided source data

The two synthetic datasets the project is built on, plus the generator that
produced them (seed = 42). These are the **canonical source** files.

| File | Shape | Feeds |
|---|---|---|
| `messages.csv` | 630 × 5 | Module 1 — the Reader (LSTM training) |
| `customers.csv` | 220 × 21 | Modules 2 & 3 — Investigator + Economist |
| `generate_data.py` | — | regenerates both CSVs deterministically |

## Relationship to `backend/data/`

`backend/data/customers.csv` and `backend/data/messages.csv` are **byte-identical
copies** of the files here — the runtime location the backend loaders read from
(`backend/data/loader.py`, `backend/modules/investigator/profile_loader.py`
resolve paths relative to `backend/`). This folder is the human-facing "where the
data came from"; `backend/data/` is the deployment copy. If you regenerate the
data, copy the new CSVs into `backend/data/` as well.

> `customers.csv` contains a 21st column, `_archetype` (the ground-truth label).
> It is a **leakage trap**: dropped on load by every loader and used only inside
> tests to score the Investigator. It never reaches a module or an API response.

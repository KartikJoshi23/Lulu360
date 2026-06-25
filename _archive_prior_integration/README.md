# `_archive_prior_integration/` — quarantined divergent copies

These files come from the former **`module 4/`** tree (a prior, unmerged
integration attempt). They are **divergent duplicates** of files that already
exist in the canonical structure, kept here so no work is lost — **not** part of
the build.

| Archived file | Canonical file it conflicts with | Difference |
|---|---|---|
| `investigator.module4.py` | `backend/modules/investigator/investigator.py` (from the official Module 2 clone) | Rewritten; different import style and body |
| `enums.module4.py` | `shared/enums.py` (from the official Module 2 clone) | Different enum-constant contract |

> ⚠️ **Task 2 reconciliation item #1.** Modules 1, 3 and 4 (`reader.py`,
> `economist.py`, `voice.py`) were written against `enums.module4.py`, while the
> canonical `shared/enums.py` comes from Module 2. These two enum contracts must
> be reconciled before the pipeline can run end-to-end. This is a code-logic
> decision and was intentionally **not** made during the structure-only Task 1.

Once Task 2 resolves the enum contract, this folder can be deleted.

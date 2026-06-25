# Module 1 — The Reader — Steering Context

*2-minute brief for teammates building the other LuluCare 360 modules. Read this instead of the full notebook.*

## 1. What was built

The Reader is the NLU front-door of LuluCare 360. It takes a raw customer complaint string and returns
a structured dict. Internally it is **two independent Keras LSTM classifiers** sharing one tokenizer
and one train/test split: an **issue classifier** (7 classes) and a **frustration classifier**
(3 classes). Trained **only** on `messages.csv` (630 balanced messages) — it never touches
`customers.csv` or any profile data. The notebook also runs a SimpleRNN-vs-LSTM experiment proving the
LSTM's gated memory wins on longer messages (the vanishing-gradient insight). Everything is exposed
through one frozen function, `read_message(text)`.

## 2. Frozen output contract

```python
read_message(text: str) -> dict
```

```json
{
  "issue_type":  "Delivery",
  "frustration": "High",
  "confidence":  0.87
}
```

| Key           | Type    | Valid values                                                                                              |
|---------------|---------|----------------------------------------------------------------------------------------------------------|
| `issue_type`  | `str`   | `App_Technical`, `Billing`, `Damaged_Defective`, `Delivery`, `General_Query`, `Product_Quality`, `Refund_Return` (exact TitleCase) |
| `frustration` | `str`   | `Low`, `Medium`, `High`                                                                                   |
| `confidence`  | `float` | `[0.0, 1.0]` — softmax max of the **issue** prediction, rounded to 3 dp                                   |

Guarantees: all values are JSON-safe (no numpy types — validated with `json.dumps`). Empty/whitespace
input returns the safe fallback `{"issue_type": "General_Query", "frustration": "Low", "confidence": 0.0}`
and never crashes.

## 3. Saved artifacts (`models/` directory)

| File                            | Purpose                                                              |
|---------------------------------|---------------------------------------------------------------------|
| `models/reader_issue.keras`     | Trained LSTM issue classifier (7-class)                              |
| `models/reader_frustration.keras` | Trained LSTM frustration classifier (3-class)                     |
| `models/tokenizer.json`         | Keras tokenizer (word→id mapping; must match training)              |
| `models/label_maps.json`        | id↔label maps for both heads + `VOCAB` (3000) and `MAXLEN` (40)     |
| `reader.py`                     | Standalone module: loads the above and exposes `read_message()`      |

All four `models/` files are **required** at inference time — the `.keras` models alone are useless
without the tokenizer and label maps.

## 4. Key findings

- **LSTM beats SimpleRNN on long messages.** The two tie on short messages but the LSTM holds accuracy
  on messages above the median length, because its gated cell state preserves early-sentence context
  where the SimpleRNN's gradient vanishes. This is the project's core ML insight; the LSTM is shipped.
- **Most-confused pair: `Damaged_Defective` ↔ `Product_Quality`** (shared fault vocabulary). This is
  financially sensitive — `Damaged_Defective` auto-triggers refunds downstream — so the confidence gate
  matters here.
- **Confidence is honestly calibrated**: it drops on vague input (e.g. `"I have a question"`) vs. clear
  complaints, which is what makes the Economist's `confidence < 0.5` escalation gate trustworthy.
- *(Exact accuracy numbers print in the notebook's final summary cell; they shift slightly per run
  since these are small models on 630 messages. The short-vs-long gap is the robust, reproducible
  signal.)*

## 5. Integration notes for Module 4 (API)

1. Place `reader.py` in the backend (e.g. `backend/reader.py`) with the `models/` folder **one level
   up** from it — `reader.py` resolves artifacts at `os.path.join(os.path.dirname(__file__), '..', 'models')`.
   Typical layout:
   ```
   project/
     models/                 # the 4 saved artifacts
     backend/
       reader.py             # imports from ../models
   ```
2. Import and call:
   ```python
   from reader import read_message
   result = read_message("My delivery never arrived and I am furious!")
   ```
3. Models load **once at import time** (module-level globals), so the first import is slow but each
   `read_message()` call is fast. Import `reader` at API startup, not per-request.
4. Requires `tensorflow` in the backend environment.
5. Output is already JSON-safe — return it directly from FastAPI without further casting.

## 6. Caveats / known limitations

- **Small training set** (630 short messages, ~14 words avg). Models are deliberately small; expect
  some run-to-run variance and limited generalization to phrasing far outside the training distribution.
- **`Damaged_Defective` ↔ `Product_Quality` overlap** is the main residual error and is financially
  sensitive — rely on the confidence gate, don't assume the issue label is always right.
- **Confidence is the issue model's softmax max**, not a frustration confidence. The frustration label
  has no confidence score in the contract.
- **`MAXLEN=40`** truncates anything longer than 40 tokens (no training message exceeds 23, so this is
  safe headroom, but very long real-world pastes would be clipped).
- Reproducible via `random_state=42` and seeded RNGs, but TensorFlow GPU nondeterminism can still cause
  tiny differences across machines.

# Deploying LuluCare 360

Two pieces deploy separately: the **React frontend** (static → Netlify) and the
**Python API** (a live process → Render/Railway). Netlify cannot run Python.

---

## 1. Backend → Render (free tier)

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → select the repo. `render.yaml` provisions a
   web service:
   - build: `pip install -r backend/requirements-deploy.txt`
   - start: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`
   - `LULU_DISABLE_FLAN=1` (template Voice + keyword Reader — light + fast)
3. After the first deploy, set the **`NETLIFY_ORIGIN`** env var to your Netlify
   site URL (e.g. `https://lulucare360.netlify.app`) so CORS allows it.
4. Verify: `GET https://<your-api>.onrender.com/health` → `{"status":"ok", ...}`.

> Free dynos sleep when idle; the first request after a nap is slow. The
> frontend's **demo mode** (below) covers grading even if the API is asleep.

To run the **real LSTM Reader + FLAN-T5 Voice** in the cloud instead, deploy
with `backend/requirements.txt`, drop `LULU_DISABLE_FLAN`, and ship the
`backend/models/*.keras` artifacts (regenerate via
`python backend/modules/reader/train_reader.py`).

---

## 2. Frontend → Netlify (free tier)

1. Netlify → **Add new site → Import from Git** → select the repo.
   `frontend/netlify.toml` sets base `frontend`, build `npm run build`,
   publish `dist`, and the SPA redirect.
2. Set environment variables in the Netlify dashboard:
   - `VITE_API_BASE_URL` = `https://<your-api>.onrender.com`
   - `VITE_DEMO_MODE` = `false`  (or `true` for the static demo — see below)
3. Deploy. Open the site; the Health pill should read **API · …**.

---

## 3. Static demo-mode fallback (no backend needed)

Set **`VITE_DEMO_MODE=true`** on Netlify (or in `frontend/.env.local` locally).
The dashboard then serves precomputed responses from `frontend/src/demoData.ts`
for the curated handbook customers — perfect when the backend is unavailable.

Regenerate the fixtures any time after backend changes:

```bash
python backend/scripts/gen_demo_data.py   # writes frontend/src/demoData.ts
```

---

## 4. Local development (both together)

```bash
# Terminal 1 — API
pip install -r backend/requirements.txt
python backend/modules/reader/train_reader.py        # optional: enables the LSTM
uvicorn backend.api.main:app --reload --port 8000

# Terminal 2 — dashboard
cd frontend && npm install && npm run dev            # http://localhost:5173
```

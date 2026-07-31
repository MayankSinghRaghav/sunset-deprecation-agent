# Deploying Sunset on Render

Sunset hosts as **three services**, defined in one **[`render.yaml`](render.yaml)**
Blueprint:

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│ sunset-db   │◀────│ sunset-backend   │◀────│ sunset-frontend      │
│ Postgres    │     │ FastAPI +        │     │ Next.js UI, reads the │
│ (pgvector)  │     │ LangGraph        │     │ backend via /catalogue │
└─────────────┘     └──────────────────┘     └──────────────────────┘
```

- **sunset-db** — managed Postgres. The backend enables `pgvector` on boot; if
  it isn't available it transparently falls back to a numpy vector index.
- **sunset-backend** — applies the schema, seeds the committed fixtures, runs the
  pipeline **once** in offline mode (no API key), then serves the API. First
  deploy takes ~1–2 minutes while the pipeline runs.
- **sunset-frontend** — the Next.js app. It reads real audit data from the
  backend; the backend URL is wired in automatically via the Blueprint.

Everything is committed and wired. The steps below are the account-level actions
only you can do (they need your Render login).

---

## One-click Blueprint

1. Sign in to [Render](https://render.com) and connect this GitHub repository.
2. **New → Blueprint**, select this repo. Render reads `render.yaml` and shows
   the three resources (`sunset-db`, `sunset-backend`, `sunset-frontend`).
3. **Apply.** Render provisions the database, then builds and deploys both
   services. The frontend's `NEXT_PUBLIC_API_BASE` is populated from the backend
   service automatically (`fromService`), so no manual URL wiring is needed.
4. Watch `sunset-backend`'s logs: waiting for Postgres → schema/roles/indexes →
   seeding fixtures → running the pipeline → `starting API on :$PORT`. When its
   health check (`/`) is green, open the **sunset-frontend** URL — the catalogue,
   memos, citation exhibits, overrides, and scorecard all render real pipeline
   output.

That's the whole deploy. Every push to your default branch redeploys.

---

## Verify

- Backend: `GET https://sunset-backend-…onrender.com/` → product JSON;
  `/catalogue` → 40 rows; `/features/f23/memo-view` → a full structured memo.
- Frontend: open a memo and use **Override verdict** — it POSTs to the backend,
  which records the decision and resumes the graph through the human gate
  (checkpoint/resume); the UI then reflects the persisted verdict.

## Tighten CORS (optional)

The Blueprint sets `SUNSET_CORS_ORIGINS=*` so the frontend works immediately. To
lock it down: on `sunset-backend` → Environment, set `SUNSET_CORS_ORIGINS` to the
frontend's URL and save (redeploys automatically).

## If the frontend shows mock data

`NEXT_PUBLIC_API_BASE` is baked into the client bundle at **build time**. If for
any reason the automatic wiring didn't take, set it explicitly on
`sunset-frontend` → Environment to the backend's full URL
(`https://sunset-backend-…onrender.com`) and **Manual Deploy → Clear build cache
& deploy**. A scheme-less host is fine — the app defaults it to `https://`.

## Notes on the numbers

- In **offline** mode the memos, verdicts, citations, at-risk accounts, and the
  reconciler's decision trace are all genuine pipeline output. The scorecard's
  **agent accuracy headline stays suppressed** — the offline stub is not a model
  score, and the system refuses to present one as if it were. The deterministic
  baseline (32.5%) and the per-trap counts are real.
- For a real **model** score, set on `sunset-backend`:
  `SUNSET_LLM_MODE=live` and `GEMINI_API_KEY=<key>`, then redeploy (or clear
  `audit_runs` and let the entrypoint re-run). Mind the Gemini free-tier quota.

## Free tier & restarts

Free web services spin down after ~15 minutes idle and cold-start on the next
request. The entrypoint is idempotent: on restart it re-applies the schema
(no-ops), skips seeding when the catalogue is present, and skips the pipeline
when a completed run already exists — so cold starts are fast (no re-run). Free
Postgres has storage/retention limits suitable for a demo.

---

## Other platforms

The backend (`Dockerfile` + `docker/entrypoint.sh`) and frontend
(`frontend/Dockerfile`, standalone output) are standard containers and run
anywhere. A `railway.json` for each service is also committed for Railway; the
same `DATABASE_URL` / `NEXT_PUBLIC_API_BASE` contract applies on Fly.io,
DigitalOcean App Platform, Cloud Run, etc.

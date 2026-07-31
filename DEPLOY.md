# Deploying Sunset on Railway

Sunset hosts as **three services** in one Railway project:

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  Postgres   │◀────│  backend (API)   │◀────│  frontend (Next.js)  │
│  + pgvector │     │  FastAPI +       │     │  reads the API via   │
│             │     │  LangGraph       │     │  NEXT_PUBLIC_API_BASE │
└─────────────┘     └──────────────────┘     └──────────────────────┘
```

- **Postgres** stores the catalogue, evidence, and audit results.
- **backend** applies the schema, seeds the committed fixtures, runs the pipeline
  **once** in offline mode (no API key needed), then serves the API. First boot
  takes ~1–2 minutes while the pipeline runs; the healthcheck timeout allows for it.
- **frontend** is the Next.js UI. It reads real audit data from the backend; the
  backend URL is baked in at build time via `NEXT_PUBLIC_API_BASE`.

Everything in this repo is committed and ready — the steps below are the
account-level actions only you can do (they need your Railway login). Each
service's build config is already declared in a `railway.json`, and the
Dockerfiles do the rest.

---

## Prerequisites

- A [Railway](https://railway.app) account.
- This repository connected to Railway (GitHub integration, or `railway up` from
  the CLI). The steps below use the dashboard.

---

## Step 1 — Create the project and the database

1. **New Project → Deploy PostgreSQL.** Railway provisions a managed Postgres and
   exposes a `DATABASE_URL` variable on that service.
   - The backend detects whether `pgvector` is available and picks its vector
     backend automatically (pgvector if present, otherwise a numpy brute-force
     index — both work at this scale). If you want the pgvector path guaranteed,
     add a service from the Docker image `pgvector/pgvector:pg16` instead of the
     stock Postgres, with a volume at `/var/lib/postgresql/data` and
     `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` set.

## Step 2 — Deploy the backend

1. **New Service → GitHub Repo →** this repository.
2. **Settings → Root Directory:** leave as the repo root (`/`). Railway will pick
   up `railway.json` and build the root `Dockerfile`.
3. **Variables** (Service → Variables):
   - `DATABASE_URL` → reference the Postgres service: `${{Postgres.DATABASE_URL}}`
   - `SUNSET_LLM_MODE=offline`  *(real pipeline output, no key needed)*
   - `SUNSET_EMBEDDING_MODEL=hashing-v1`
   - `SUNSET_CORS_ORIGINS=*`  *(tighten to the frontend URL after Step 3)*
4. **Networking → Generate Domain.** Note the public URL, e.g.
   `https://sunset-backend-production.up.railway.app`.
5. Watch the deploy logs. You'll see: waiting for Postgres → schema/roles/indexes
   → seeding fixtures → running the pipeline → `starting API on :8000`. When the
   healthcheck on `/` goes green, hit the URL — it returns the product JSON, and
   `/{that-url}/catalogue` returns 40 real audited features.

## Step 3 — Deploy the frontend

1. **New Service → GitHub Repo →** this repository (same repo, second service).
2. **Settings → Root Directory: `frontend`.** Railway uses `frontend/railway.json`
   and `frontend/Dockerfile`.
3. **Variables:**
   - `NEXT_PUBLIC_API_BASE` → the backend's public URL from Step 2
     (e.g. `https://sunset-backend-production.up.railway.app`).
     Railway passes it as the Docker build arg, so it's inlined into the client
     bundle. **A change here requires a redeploy** (it's build-time).
4. **Networking → Generate Domain.** This is your app URL.

## Step 4 — Lock down CORS

Back on the **backend** service, set `SUNSET_CORS_ORIGINS` to the frontend's
public URL (comma-separated if more than one) and redeploy. The API will then
accept browser requests only from your frontend.

---

## Verify

- Backend: `GET https://<backend>/` → product JSON; `GET /catalogue` → 40 rows;
  `GET /features/f23/memo-view` → a full structured memo.
- Frontend: open the app URL. The catalogue, memos, the citation exhibits, and the
  scorecard all render **real** pipeline output. Open a memo and use **Override
  verdict** — it POSTs to the backend, which records the decision and resumes the
  graph through the human gate (checkpoint/resume), then the UI reflects the
  persisted verdict.

## Notes on the numbers

- In **offline** mode the memos, verdicts, citations, at-risk accounts, and the
  reconciler's decision trace are all genuine pipeline output. The **scorecard's
  agent accuracy headline stays suppressed** — this is deliberate: the offline
  stub is not a model score, and the system refuses to present one as if it were.
  The deterministic baseline (32.5%) and the per-trap counts are real.
- For a real **model** accuracy number, set on the backend service:
  - `SUNSET_LLM_MODE=live`
  - `GEMINI_API_KEY=<your key>`
  then trigger a fresh run (redeploy, or `POST /runs`). Note Gemini free-tier
  quotas; a full 40-feature run needs sufficient daily quota or billing enabled.

## Redeploys and data

The backend entrypoint is idempotent: on restart it re-applies the schema
(no-ops if present), skips seeding when the catalogue is already loaded, and
skips the pipeline when a completed run already exists. To force a fresh run,
clear `audit_runs` in the database (or trigger `POST /runs`) and redeploy.

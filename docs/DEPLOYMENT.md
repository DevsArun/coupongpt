# CouponGPT — Deployment Guide

The backend is a single, stateless Docker image that reads **all** infrastructure
endpoints from environment variables. This means the same image runs unchanged on
Hugging Face Spaces, a VPS, a cloud VM, or a dedicated server — only the env
differs. The PHP frontend is a separate image/host that talks to the backend over
HTTP.

```
Browser ─► PHP Frontend ─► FastAPI Backend ─► MySQL / Redis / Meilisearch
```

---

## 1. Local development (Docker Compose)

```bash
cp .env.example .env          # fill in AI + payment keys (optional for demo)
docker compose up --build
```

| Service     | URL                          |
|-------------|------------------------------|
| Frontend    | http://localhost:8080        |
| Backend API | http://localhost:8000/docs   |
| Meilisearch | http://localhost:7700        |

The MySQL container auto-runs the migrations in `backend/migrations/` on first
boot (mounted into `/docker-entrypoint-initdb.d`). Then seed and index:

```bash
docker compose exec backend python -m app.cli create-admin admin@coupongpt.dev 'ChangeMe123!'
docker compose exec backend python -m app.cli seed          # demo coupons
docker compose exec backend python -m app.cli reindex        # push to Meilisearch
docker compose exec backend python -m app.cli sync-synonyms  # synonyms -> Meili
```

## 2. Backend only (no Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # point MYSQL_/REDIS_/MEILI_ at your services
uvicorn app.main:app --reload
```

Apply the schema manually:

```bash
mysql -u root -p coupongpt < migrations/001_schema.sql
mysql -u root -p coupongpt < migrations/002_seed.sql
```

## 3. Hugging Face Spaces (backend)

HF Spaces (Docker SDK) builds the image and runs it, expecting the app to listen
on `$PORT` (default **7860**). The backend `Dockerfile` already honours `$PORT`,
so no changes are needed.

1. Create a **Docker** Space.
2. Add `backend/` as the build context (or point the Space at this repo and set
   the Dockerfile path to `backend/Dockerfile`).
3. In **Settings → Variables and secrets**, add the env from `.env.example`:
   - `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` (or a single `DATABASE_URL`)
   - `REDIS_URL` (or `REDIS_HOST/PORT/PASSWORD`)
   - `MEILI_HOST`, `MEILI_MASTER_KEY`
   - `JWT_SECRET`, `APP_SECRET_KEY`
   - AI keys: `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`
   - Payment keys (optional): `STRIPE_*`, `RAZORPAY_*`
   - `CORS_ORIGINS` = your frontend origin
4. Use **managed/hosted** data stores (Spaces have no persistent DB):
   - MySQL: PlanetScale / Railway / RDS / Aiven
   - Redis: Upstash / Redis Cloud
   - Meilisearch: Meilisearch Cloud (set `MEILI_HOST`/`MEILI_MASTER_KEY`)
5. After first boot, run the migrations against your managed MySQL, then trigger
   `reindex` (e.g. via a one-off job or the admin "Reindex all" button).

> A minimal Space `README.md` front-matter is provided at
> `backend/SPACE_README.md` — copy its contents to the Space's README to set the
> SDK and app port.

## 4. VPS / Cloud VM / dedicated server

No business-logic changes are required — this is by design.

**Option A — Compose (simplest):** copy the repo, set `.env`, run
`docker compose up -d`. Put Nginx/Caddy in front for TLS.

**Option B — Native:** run MySQL, Redis, and Meilisearch as system services;
run the backend under a process manager:

```bash
gunicorn -k uvicorn.workers.UvicornWorker app.main:app \
  --bind 0.0.0.0:8000 --workers 4
```

Serve the PHP frontend with Apache/PHP-FPM or the provided `frontend/Dockerfile`,
and set `BACKEND_BASE_URL` to the backend's internal address.

### Migration checklist (Spaces → VPS)
1. Export MySQL (`mysqldump`) and import on the new host.
2. Re-point `MYSQL_*`, `REDIS_*`, `MEILI_*` env vars.
3. Run `python -m app.cli reindex` to rebuild the Meilisearch index.
4. Update `CORS_ORIGINS` and the frontend's `BACKEND_BASE_URL`.

## 5. Operations

| Task | Command |
|------|---------|
| Create/promote admin | `python -m app.cli create-admin EMAIL PASSWORD` |
| Seed demo coupons | `python -m app.cli seed` |
| Rebuild search index | `python -m app.cli reindex` |
| Sync synonyms | `python -m app.cli sync-synonyms` |
| Run ingestion (due sources) | `python -m app.cli ingest` |
| Expire stale coupons | `python -m app.cli expire` |

Schedule `ingest` and `expire` via cron / a scheduled job (e.g. every few hours).

## 6. Backups & monitoring

- **Backups:** nightly `mysqldump` (retain 7–30 days); Meilisearch is rebuildable
  from MySQL via `reindex`, so MySQL is the only stateful backup target.
- **Health:** `GET /api/v1/health` (liveness) and `GET /api/v1/ready` (checks
  MySQL/Redis/Meili) for load balancers and uptime monitors.
- **Logs:** structured JSON logs (set `LOG_JSON=true`) ship cleanly to any log
  aggregator. Set `SENTRY_DSN` to enable error tracking.
- **Metrics:** every response carries `X-Response-Time-ms`; search latency is also
  recorded per query in `search_queries` and surfaced in the admin dashboard.

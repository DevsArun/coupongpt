# CouponGPT — AI Coupon Search SaaS Platform

> An enterprise-grade, AI-powered coupon search platform. Users search in natural
> language ("best amazon coupon today", "bst niek coupn") and get ranked, validated
> coupon results from a pre-indexed internal database — never scraped at query time.

[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)]()
[![Frontend](https://img.shields.io/badge/frontend-PHP%208.4-777bb4)]()
[![Search](https://img.shields.io/badge/search-Meilisearch-ff5caa)]()
[![DB](https://img.shields.io/badge/db-MySQL%208-00758f)]()

---

## What it does

- **Natural-language + typo-tolerant search** — understands merchant, time intent,
  and discount intent even with misspellings.
- **AI query understanding** with a multi-provider fallback chain
  (Groq → Gemini → OpenAI).
- **Sub-200ms search** powered by Meilisearch over a pre-indexed coupon corpus.
- **Multi-source coupon discovery pipeline** (merchant pages, RSS, sitemaps,
  newsletters, user submissions) with AI structuring, dedup, validation & scoring.
- **Subscriptions & billing** via Stripe and Razorpay (recurring, webhooks,
  invoices, retries, refunds).
- **Super-admin mission control** and a **user dashboard** (saved coupons,
  watchlists, deal alerts, referrals).
- **Enterprise security**: JWT + refresh tokens, RBAC, rate limiting, audit logs.

## Architecture at a glance

```
Browser
  │
  ▼
PHP Frontend  ── renders UI, holds session, proxies to backend
  │  (HTTPS, server-to-server)
  ▼
FastAPI Backend ── APIs, auth, search, AI, billing, ingestion, analytics
  │
  ├── MySQL 8         (durable source of truth)
  ├── Redis           (cache, quotas, rate limits, queues)
  └── Meilisearch     (search index)
```

Frontend and backend are **fully separated**. The PHP tier never touches the
database directly — it only talks to the FastAPI backend over HTTP.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full design and
[`docs/`](./docs) for the ERD, API, deployment, and security guides.

## Repository layout

```
coupongpt/
├── ARCHITECTURE.md          # System design, data flow, scaling
├── docker-compose.yml       # Local dev: backend, frontend, mysql, redis, meili
├── .env.example             # All configuration knobs
├── docs/                    # ERD, API, deployment, security
├── backend/                 # FastAPI application (Python)
│   ├── app/                 # Source (core, models, schemas, api, services, ai, search, ingestion, billing)
│   ├── migrations/          # SQL schema + seed data
│   ├── tests/               # pytest suites
│   └── requirements.txt
└── frontend/                # PHP 8.4 application (Tailwind + vanilla JS)
    ├── public/              # Web root
    └── src/                 # Pages, partials, lib, admin
```

## Quick start (local, Docker)

```bash
cp .env.example .env          # fill in AI keys & payment keys
docker compose up --build
```

- Frontend:  http://localhost:8080
- Backend:   http://localhost:8000/docs  (OpenAPI)
- Meilisearch: http://localhost:7700

Then seed and index:

```bash
docker compose exec backend python -m app.cli seed       # plans, roles, sample data
docker compose exec backend python -m app.cli reindex    # push coupons to Meilisearch
```

## Quick start (backend only, no Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload
```

## Deployment

- **Hugging Face Spaces** (Docker SDK) for the backend — see
  [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).
- **VPS / Cloud VM / dedicated** migration without business-logic changes — the
  app reads all infrastructure endpoints from environment variables.

## Phase status

This platform is built in 10 phases. See the phase tracker in
[`ARCHITECTURE.md`](./ARCHITECTURE.md#build-phases).

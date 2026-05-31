---
title: CouponGPT Backend
emoji: 🎟️
colorFrom: orange
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# CouponGPT Backend (FastAPI)

This Space hosts the CouponGPT API. The container listens on `$PORT` (default
**8000**), and the `app_port: 8000` above tells Hugging Face to route to it — keep
the two in sync. (Prefer 7860? Set `app_port: 7860` **and** a Space variable
`PORT=7860`.)

The image is build-light on purpose: it uses the pure-Python `aiomysql` driver and
wheel-only deps, so there's **no compiler step** — Spaces build fast.

Configure these **secrets/variables** in the Space settings:

- `DATABASE_URL` (e.g. `mysql+aiomysql://user:pass@host:3306/coupongpt`)
- `REDIS_URL` (e.g. `redis://default:pass@host:6379/0`)
- `MEILI_HOST`, `MEILI_MASTER_KEY`
- `JWT_SECRET`, `APP_SECRET_KEY` (strong, >=16 chars — required in production)
- `APP_ENV=production`, `APP_DEBUG=false`
- `CORS_ORIGINS` (your frontend origin — not `*`)
- `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY` (optional)
- `STRIPE_*`, `RAZORPAY_*` (optional)

Use **managed** data stores (Spaces have no persistent DB): PlanetScale/RDS/Aiven
(MySQL), Upstash/Redis Cloud (Redis), Meilisearch Cloud.

After first boot, apply the schema and index from a one-off job or locally against
the same managed DB:

```bash
python -m app.cli migrate     # create tables + seed
python -m app.cli reindex     # push coupons to Meilisearch
```

API docs are served at `/docs`. Health at `/api/v1/health`.

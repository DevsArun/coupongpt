---
title: CouponGPT Backend
emoji: 🎟️
colorFrom: orange
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# CouponGPT Backend (FastAPI)

This Space hosts the CouponGPT API. It listens on `$PORT` (7860 on Spaces).

Configure these **secrets/variables** in the Space settings:

- `DATABASE_URL` (e.g. `mysql+asyncmy://user:pass@host:3306/coupongpt`)
- `REDIS_URL` (e.g. `redis://default:pass@host:6379/0`)
- `MEILI_HOST`, `MEILI_MASTER_KEY`
- `JWT_SECRET`, `APP_SECRET_KEY`
- `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY` (optional)
- `STRIPE_*`, `RAZORPAY_*` (optional)
- `CORS_ORIGINS` (your frontend origin)

API docs are served at `/docs`. Health at `/api/v1/health`.

# CouponGPT — System Architecture

This document is the single source of truth for the platform design. It is written
to be read by every role on the team (PM, architects, backend, frontend, AI,
search, DB, security, DevOps, QA, perf) at their preferred depth.

---

## 1. Goals & non-negotiables

| Requirement | Design decision |
|---|---|
| Search must be **fast** (<200ms) | Meilisearch over a pre-indexed corpus; AI runs only for *query understanding*, not retrieval, and is cached. |
| Search must **never scrape at query time** | All retrieval is from MySQL/Meilisearch. Crawling happens in an offline ingestion pipeline. |
| Frontend ↔ backend **fully separated** | PHP renders UI + holds session; FastAPI owns all data/business logic. PHP never connects to MySQL/Redis/Meili. |
| Deployable on **Hugging Face Spaces**, portable to VPS | All infra endpoints are env-driven; backend is a single Docker image; no hard dependency on a specific host. |
| Designed for **millions of records** | Normalized schema, careful indexes, partition-friendly keys, Redis caching, async I/O. |
| **Enterprise security** | JWT + rotating refresh tokens, RBAC, rate limiting, audit logging, parameterized queries via ORM. |

## 2. High-level topology

```
                         ┌─────────────────────────────┐
            Browser ───► │   PHP Frontend (Apache/PHP)  │
                         │  - SSR pages (Tailwind/JS)   │
                         │  - PHP session + CSRF         │
                         │  - BackendClient (HTTP proxy) │
                         └──────────────┬───────────────┘
                                        │  HTTPS, Bearer (server-side)
                                        ▼
                         ┌─────────────────────────────┐
                         │     FastAPI Backend (ASGI)   │
                         │  api/ services/ ai/ search/  │
                         │  ingestion/ billing/         │
                         └───┬───────────┬───────────┬──┘
                             │           │           │
                   ┌─────────▼──┐  ┌─────▼─────┐ ┌───▼────────┐
                   │  MySQL 8   │  │  Redis 7  │ │ Meilisearch│
                   │ source of  │  │ cache /   │ │  search    │
                   │  truth     │  │ quota /   │ │  index     │
                   │            │  │ queue     │ │            │
                   └────────────┘  └───────────┘ └────────────┘
                                        ▲
                                        │ (background workers)
                          ┌─────────────┴──────────────┐
                          │  Ingestion / Validation /  │
                          │  Indexing workers (cron/    │
                          │  queue-driven)              │
                          └─────────────────────────────┘
```

## 3. Component responsibilities

### 3.1 PHP Frontend (`frontend/`)
- Server-side rendered pages with Tailwind + vanilla JS.
- Owns the **browser session** (PHP `$_SESSION`), CSRF tokens, and cookies.
- Holds the user's backend tokens **server-side** (never exposed to JS) and
  forwards authenticated calls through a thin `BackendClient`.
- Zero business logic — purely presentation, navigation, and request shaping.

### 3.2 FastAPI Backend (`backend/`)
The only tier with credentials to data stores. Modules:
- `core/` — config, DB session, Redis, logging, security primitives, middleware.
- `models/` — SQLAlchemy ORM (async) mapped 1:1 to the schema.
- `schemas/` — Pydantic request/response contracts.
- `api/v1/` — versioned REST endpoints + dependency wiring.
- `services/` — business logic (auth, users, quota, subscriptions, analytics…).
- `ai/` — provider abstraction + fallback chain + query understanding.
- `search/` — Meilisearch client, index config, query builder, ranking.
- `ingestion/` — discovery → crawl → clean → extract → structure → dedup →
  validate → score → store → index.
- `billing/` — Stripe & Razorpay gateways, webhooks, invoices, retries.

### 3.3 Data stores
- **MySQL 8** — durable source of truth. InnoDB, `utf8mb4`, FK constraints.
- **Redis 7** — response cache, search-result cache, **quota counters**, rate-limit
  buckets, ephemeral job queue, refresh-token denylist.
- **Meilisearch** — the only retrieval path for search. Configured with typo
  tolerance, synonyms, merchant aliases, ranking rules, filterable/sortable attrs.

## 4. The search request lifecycle (the hot path)

```
GET /api/v1/search?q=bst niek coupn
  1. Auth + quota check (Redis counter; 429 if exhausted)
  2. Cache lookup: key = hash(normalized_q + filters + plan)        ── Redis
       hit  -> return immediately (<5ms)
  3. Query understanding (AI, cached by normalized q)               ── Redis/AI
       -> { merchant: "nike", time_intent: null, discount_intent: null,
            corrected_q: "best nike coupon", confidence: 0.83 }
  4. Build Meilisearch query (typo tolerance + merchant filter + synonyms)
  5. Retrieve candidates from Meilisearch                            ── Meili
  6. Re-rank with multi-factor score (relevance × trust × freshness …)
  7. Record analytics (async, fire-and-forget)                       ── MySQL
  8. Cache + return ranked results
```

**Why this hits <200ms:** steps 2 cache the whole thing; step 3 is cached per
distinct query so the AI call is amortized; retrieval (5) is Meilisearch's
millisecond path; re-ranking (6) is in-memory over ≤ N candidates.

## 5. Coupon ingestion pipeline (offline)

```
Source Discovery → Crawler → Cleaner → Extraction → AI Structuring
   → Deduplication → Validation → Scoring → Storage(MySQL) → Meilisearch Index
```

Each stage is an idempotent, resumable unit driven by a queue. Crawling is
**decoupled from search** — coupons are only searchable once they reach the index.

## 6. Validation & ranking model

Every coupon carries six component scores in `[0,1]`, combined into a single
`ranking_score`:

```
ranking_score =
      w_relevance   * relevance         (query-time, from Meili)
    + w_trust       * source_trust_score
    + w_freshness   * freshness_score
    + w_confidence  * confidence_score
    + w_success     * success_rate_score
    + w_expiry      * expiry_score
    - w_duplicate   * duplicate_penalty
```

Weights are stored in `settings` (admin-tunable). **Never rank by date alone.**

## 7. AI provider abstraction

A single `AIProvider` interface with concrete `GroqProvider`, `GeminiProvider`,
`OpenAIProvider`. An `AIRouter` walks an admin-configurable priority chain
(`Groq → Gemini → OpenAI`), with per-provider enable/disable, timeouts, and
automatic failover on error/timeout. Usage and failures are logged to
`ai_usage_logs`. Query understanding returns **structured JSON** validated by
Pydantic; on total AI failure the system degrades gracefully to a heuristic
parser (regex merchant/alias match + keyword time/discount detection).

## 8. Subscriptions & quotas

Plans (`free`, `starter`, `pro`, `yearly_pro`, `yearly_elite`, custom, lifetime)
define quota windows (`per_day` / `per_month`) and limits. Quota enforcement is a
Redis counter keyed by `quota:{user_id}:{window}:{bucket}` with a TTL aligned to
the window; the durable counts are reconciled to MySQL for analytics/billing.

## 9. Security model

- **AuthN**: short-lived JWT access tokens + long-lived rotating refresh tokens.
  Refresh tokens are stored hashed; rotation + reuse-detection via a denylist.
- **Transport**: secure, `HttpOnly`, `SameSite` cookies issued by the PHP tier;
  the browser never sees raw backend tokens.
- **AuthZ**: RBAC — roles → permissions; FastAPI dependencies enforce
  `require_permission("coupons.write")` style checks.
- **Hardening**: per-IP + per-user rate limiting, CSRF on the PHP tier, output
  escaping (XSS), ORM parameterization (SQLi), strict CORS, audit logs for all
  privileged actions, all secrets via environment variables.

## 10. Scaling & performance notes

- Backend is **stateless** → scale horizontally behind a load balancer.
- All shared state lives in Redis / MySQL / Meilisearch.
- Hot reads cached in Redis; search served from Meilisearch.
- DB designed with covering indexes for the common access patterns (see ERD).
- Ingestion workers scale independently from the API tier.

## 11. Deployment targets

| Target | How |
|---|---|
| Hugging Face Spaces | Single backend Docker image, port 7860; external managed MySQL/Redis/Meili via env. |
| VPS / Cloud VM | `docker-compose.yml` brings up the full stack; or run services natively. |
| Dedicated | Same image; point env at managed/self-hosted infra. |

No business logic changes between targets — only environment variables differ.

## 12. Build phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Architecture, DB schema, folder structure | ▶ in progress |
| 2 | Backend foundation | ⏳ |
| 3 | Auth + RBAC | ⏳ |
| 4 | Search engine | ⏳ |
| 5 | Coupon + validation engine | ⏳ |
| 6 | Super admin panel | ⏳ |
| 7 | User dashboard | ⏳ |
| 8 | Billing | ⏳ |
| 9 | AI layer | ⏳ |
| 10 | Testing + validation | ⏳ |

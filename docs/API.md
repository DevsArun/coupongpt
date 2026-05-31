# CouponGPT — API Reference

Base URL: `{BACKEND}/api/v1`  ·  Interactive docs: `GET /docs` (Swagger) and
`GET /redoc`. All responses are JSON. Errors use a consistent envelope:

```json
{ "error": { "code": "quota_exceeded", "message": "…", "detail": { } } }
```

Auth: send `Authorization: Bearer <access_token>` (or rely on the PHP tier's
server-side token). Tokens come from the auth endpoints below.

---

## Health
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | – | Liveness probe |
| GET | `/ready` | – | Readiness (checks MySQL, Redis, Meilisearch) |
| GET | `/version` | – | Service/version info |

## Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | – | Create account → `{user, tokens}` |
| POST | `/auth/login` | – | Login → `{user, tokens}` |
| POST | `/auth/refresh` | – | Rotate refresh → new `{tokens}` |
| POST | `/auth/logout` | – | Revoke a refresh token |
| POST | `/auth/logout-all` | ✓ | Revoke all sessions |
| GET | `/auth/me` | ✓ | Current user |
| PATCH | `/auth/me` | ✓ | Update name/timezone |
| POST | `/auth/change-password` | ✓ | Change password (revokes sessions) |

## Search
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/search?q=…&limit=` | optional | AI search; consumes one quota unit. Returns `{intent, results, total, latency_ms, cache_hit}` |
| GET | `/search/suggest?q=` | – | Autocomplete suggestions |
| GET | `/search/quota` | optional | Current quota status |

**Intent object:** `{corrected_query, merchant, merchant_id, discount_intent,
time_intent, keywords, confidence, source}`.

## Coupons (public)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/coupons/{uuid}` | – | Coupon detail (records a view) |
| GET | `/coupons/by-merchant/{merchant_id}` | – | Paginated active coupons |
| GET | `/coupons/{uuid}/go` | – | Click-out redirect (records a click) |
| POST | `/coupons/{uuid}/feedback` | optional | Report worked / didn't work |
| POST | `/coupons/submit` | optional | Submit a coupon (pending review) |

## Merchants (public)
| Method | Path | Description |
|---|---|---|
| GET | `/merchants?q=&page=&page_size=` | List/search merchants |
| GET | `/merchants/{slug}` | Merchant detail |

## Me (authenticated dashboard)
| Method | Path | Description |
|---|---|---|
| GET/POST/DELETE | `/me/saved` · `/me/saved/{uuid}` | Saved coupons |
| GET/POST/DELETE | `/me/watchlist` · `/me/watchlist/{id}` | Merchant watchlist |
| GET/POST/DELETE | `/me/alerts` · `/me/alerts/{id}` | Deal alerts |
| GET | `/me/notifications` · `/me/notifications/unread-count` | Notifications |
| POST | `/me/notifications/read-all` | Mark all read |
| GET | `/me/history` | Search history |
| GET | `/me/referrals` | Referral summary + invite link |
| GET | `/me/subscription` | Current plan & quota |

## Billing
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/billing/plans` | – | Public plan catalog |
| POST | `/billing/checkout` | ✓ | Start checkout (`stripe`/`razorpay`); demo-activates if unconfigured |
| POST | `/billing/change-plan` | ✓ | Upgrade/downgrade |
| POST | `/billing/cancel` | ✓ | Cancel (at period end or now) |
| GET | `/billing/invoices` · `/billing/payments` | ✓ | History |
| POST | `/billing/refund/{payment_id}` | `billing.refund` | Refund |
| POST | `/billing/webhooks/stripe` · `/billing/webhooks/razorpay` | – (signed) | Gateway webhooks |

## Admin (`/admin`, RBAC-guarded)
| Area | Endpoints |
|---|---|
| Dashboard | `GET /admin/dashboard` |
| Catalog | `GET/POST/PATCH /admin/merchants`, `POST /admin/merchants/{id}/aliases`, `GET/POST /admin/sources`, `POST /admin/sources/{id}/run`, `GET /admin/crawl-jobs` |
| Coupons | `GET/POST/PATCH /admin/coupons`, `POST /admin/coupons/{id}/moderate`, `/rescore`, `POST /admin/coupons/reindex`, `/expire-stale` |
| AI | `GET /admin/ai/providers`, `PATCH /admin/ai/providers/{slug}`, `GET /admin/ai/usage` |
| Analytics | `GET /admin/analytics/search`, `GET /admin/analytics/revenue` |
| People | `GET/PATCH /admin/users`, `GET /admin/subscriptions`, `GET /admin/billing/payments`, `/invoices` |
| System | `GET /admin/logs`, `GET /admin/queues`, `GET/PATCH /admin/feature-flags`, `GET /admin/settings`, `PUT /admin/settings/{key}` |

## Quotas

Each `/search` call consumes one unit against the user's plan window
(`day`/`month`). On exhaustion the API returns **429** with
`{"error":{"code":"quota_exceeded", …}}`. Anonymous users get a small per-IP
daily allowance.

| Plan | Quota |
|------|-------|
| Free | 10 / day |
| Starter ($5/mo) | 100 / month |
| Pro ($10/mo) | 200 / month |
| Yearly Pro ($49/yr) | 100 / day |
| Yearly Elite ($99/yr) | 200 / day |

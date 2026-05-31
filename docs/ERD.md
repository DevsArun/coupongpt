# CouponGPT — Entity Relationship Diagram

The full DDL lives in [`backend/migrations/001_schema.sql`](../backend/migrations/001_schema.sql).
This document explains the relationships and the reasoning behind key indexes.

## Domains

1. **Identity & access** — `roles`, `permissions`, `role_permissions`, `users`,
   `refresh_tokens`, `password_resets`, `audit_logs`
2. **Catalog** — `merchants`, `merchant_aliases`, `categories`
3. **Ingestion** — `sources`, `crawl_jobs`
4. **Coupons** — `coupons`, `coupon_categories`, `coupon_validation_events`,
   `coupon_feedback`
5. **User engagement** — `saved_coupons`, `watchlists`, `deal_alerts`,
   `notifications`, `referrals`
6. **Search** — `search_queries`, `synonyms`
7. **Billing** — `plans`, `subscriptions`, `payment_methods`, `payments`,
   `invoices`, `webhook_events`
8. **System** — `ai_providers`, `ai_usage_logs`, `feature_flags`, `settings`,
   `queue_jobs`

## Relationship map (textual ERD)

```
roles 1───* role_permissions *───1 permissions
roles 1───* users
users 1───* refresh_tokens
users 1───* password_resets
users 1───* audit_logs              (actor_id, nullable for system)
users 0..1 ◄─ users.referred_by     (self-referential referral)

merchants 1───* merchant_aliases
merchants 1───* sources
merchants 1───* coupons
merchants 1───* watchlists
merchants 1───* deal_alerts

categories 0..1 ◄─ categories.parent_id      (tree)
categories *───* coupons  (via coupon_categories)

sources 1───* crawl_jobs
sources 1───* coupons     (source_id, nullable)

coupons 1───* coupon_validation_events
coupons 1───* coupon_feedback
coupons 1───* saved_coupons

users 1───* saved_coupons
users 1───* watchlists
users 1───* deal_alerts
users 1───* notifications
users 1───* referrals (referrer_id)
users 1───* search_queries

plans 1───* subscriptions
users 1───* subscriptions
users 1───* payment_methods
users 1───* payments
subscriptions 1───* payments
users 1───* invoices
subscriptions 1───* invoices
payments 1───* invoices
```

## Why these indexes

| Access pattern | Index |
|---|---|
| Resolve a search term to a merchant by alias | `merchant_aliases(alias)` + `ix_alias_value` |
| Pull active, high-ranked coupons for a merchant | `coupons(status, ranking_score)` |
| Expire coupons in batches | `coupons(status, expires_at)` |
| Find coupons needing (re)indexing | `coupons(indexed_at)` |
| Dedup on ingest | unique `coupons(content_hash)` |
| Find sources due for crawl | `sources(is_active, last_crawled_at)` |
| Idempotent webhook processing | unique `webhook_events(gateway, event_id)` |
| Quota/billing lookups | `subscriptions(status)`, `subscriptions(current_period_end)` |
| Refresh-token rotation & reuse detection | unique `refresh_tokens(token_hash)`, `family_id` |
| Analytics over time | `search_queries(created_at)`, `audit_logs(created_at)` |

## Scaling notes

- Surrogate `BIGINT UNSIGNED` PKs everywhere keep joins compact and allow >4B rows.
- `coupons` is the largest table; its hot queries are covered by composite indexes
  on `(status, ranking_score)` and `(status, expires_at)`.
- `search_queries`, `ai_usage_logs`, and `audit_logs` are append-heavy and are good
  candidates for time-based partitioning / archival once volume grows.
- All derived/aggregate values that are read on the hot path (e.g.
  `merchants.coupon_count`) are denormalized counters updated by the ingestion and
  validation jobs.

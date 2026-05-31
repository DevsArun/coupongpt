# CouponGPT — Security Model

Security is enforced primarily at the **backend** (the only tier with data-store
credentials). The PHP frontend adds browser-session hardening (CSRF, HttpOnly
cookies) and never exposes raw API tokens to JavaScript.

---

## Authentication

- **Access tokens**: short-lived signed JWTs (`HS256`, default 30 min) carrying
  `sub`, `role`, and `perms`. Validated on every request by `get_current_user`.
- **Refresh tokens**: long, opaque random strings (`secrets.token_urlsafe(48)`).
  Only their **SHA-256 hash** is stored, so a DB leak never yields a usable token.
- **Rotation + reuse detection**: each refresh belongs to a `family_id`. On
  refresh the presented token is revoked and a new one issued in the same family.
  If a *previously revoked* token is presented again, the entire family is
  revoked — a classic refresh-token-theft signal.
- **Password changes** revoke all of a user's refresh tokens (force re-login).

## Passwords

- Hashed with **bcrypt** (per-password salt, configurable cost via
  `PASSWORD_BCRYPT_ROUNDS`). Login does constant-ish work even for unknown emails
  to limit user enumeration.

## Authorization (RBAC)

- Roles: `super_admin`, `admin`, `operations`, `analyst`, `moderator`, `support`,
  `user`. Roles map to granular permissions (e.g. `coupons.write`,
  `billing.refund`, `settings.write`).
- Enforced via FastAPI dependencies: `require_permission("…")` and
  `require_role("…")`. `super_admin` implicitly passes all checks.
- Every privileged action is written to `audit_logs` (actor, action, entity, IP).

## Transport & session (frontend)

- The PHP tier issues a single `HttpOnly`, `SameSite=Lax` session cookie
  (`Secure` in production). Backend tokens live **server-side** in the PHP session.
- All state-changing form posts and proxied writes require a **CSRF token**.
- The backend-for-frontend `/proxy` enforces a strict **path allow-list** to
  prevent it becoming an open proxy / SSRF vector, and gates `/admin/*` behind an
  admin role.

## Common web risks

| Risk | Mitigation |
|------|-----------|
| **SQL injection** | All DB access via SQLAlchemy with bound parameters; no string-built SQL. |
| **XSS** | All template output escaped via `App\e()` (htmlspecialchars); JSON-encoded data injected into `<script>` via `json_encode`. |
| **CSRF** | Per-session token verified on POST/PUT/PATCH/DELETE in the PHP tier and proxy. |
| **Clickjacking** | `X-Frame-Options` / `frame-ancestors` headers. |
| **MIME sniffing** | `X-Content-Type-Options: nosniff`. |
| **Rate abuse** | Per-IP fixed-window limiter (Redis) on the API + per-user search quotas. |
| **Secrets** | All secrets via environment variables; `.env` is git-ignored; only `.env.example` is committed. |

## Payments

- Webhook handlers **verify provider signatures** (Stripe `Webhook.construct_event`,
  Razorpay HMAC-SHA256) and are **idempotent** (unique on `(gateway, event_id)` in
  `webhook_events`).
- Card data is never stored — only gateway tokens/last-4 metadata.

## Security headers (every response)

`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`, and `Strict-Transport-Security` (production).

## Reporting

For a real deployment, publish a `SECURITY.txt` with a disclosure contact and
rotate `JWT_SECRET` / `APP_SECRET_KEY` on suspected compromise (this invalidates
all access tokens; refresh tokens can be mass-revoked per user).

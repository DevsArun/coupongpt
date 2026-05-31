-- =====================================================================
-- CouponGPT — Core schema (MySQL 8, InnoDB, utf8mb4)
-- Designed for millions of coupon records and high-volume search/billing.
--
-- Conventions:
--   * BIGINT UNSIGNED surrogate PKs
--   * utf8mb4_0900_ai_ci collation
--   * created_at / updated_at on every mutable table
--   * Foreign keys with explicit ON DELETE behaviour
--   * Indexes named ix_<table>_<cols>; uniques uq_<table>_<cols>
-- =====================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- RBAC: roles, permissions, role_permissions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    slug        VARCHAR(64)     NOT NULL,                 -- super_admin, admin, ops, analyst, moderator, support, user
    name        VARCHAR(128)    NOT NULL,
    description VARCHAR(255)    NULL,
    is_system   TINYINT(1)      NOT NULL DEFAULT 0,        -- system roles cannot be deleted
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_roles_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS permissions (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    slug        VARCHAR(128)    NOT NULL,                  -- e.g. coupons.read, coupons.write, billing.refund
    name        VARCHAR(128)    NOT NULL,
    category    VARCHAR(64)     NOT NULL DEFAULT 'general',
    description VARCHAR(255)    NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_permissions_slug (slug),
    KEY ix_permissions_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       BIGINT UNSIGNED NOT NULL,
    permission_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    KEY ix_role_permissions_permission (permission_id),
    CONSTRAINT fk_rp_role FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
    CONSTRAINT fk_rp_permission FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Users & auth
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    uuid              CHAR(36)        NOT NULL,
    email             VARCHAR(255)    NOT NULL,
    email_verified_at TIMESTAMP       NULL,
    password_hash     VARCHAR(255)    NOT NULL,
    full_name         VARCHAR(150)    NULL,
    role_id           BIGINT UNSIGNED NOT NULL,
    status            ENUM('active','suspended','pending','deleted') NOT NULL DEFAULT 'active',
    referral_code     VARCHAR(16)     NULL,
    referred_by       BIGINT UNSIGNED NULL,
    last_login_at     TIMESTAMP       NULL,
    timezone          VARCHAR(64)     NOT NULL DEFAULT 'UTC',
    created_at        TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_uuid (uuid),
    UNIQUE KEY uq_users_email (email),
    UNIQUE KEY uq_users_referral_code (referral_code),
    KEY ix_users_role (role_id),
    KEY ix_users_status (status),
    KEY ix_users_referred_by (referred_by),
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE RESTRICT,
    CONSTRAINT fk_users_referred_by FOREIGN KEY (referred_by) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL,
    token_hash  CHAR(64)        NOT NULL,                  -- sha256 of the raw token
    family_id   CHAR(36)        NOT NULL,                  -- rotation family for reuse detection
    user_agent  VARCHAR(255)    NULL,
    ip_address  VARBINARY(16)   NULL,
    revoked_at  TIMESTAMP       NULL,
    expires_at  TIMESTAMP       NOT NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_refresh_token_hash (token_hash),
    KEY ix_refresh_user (user_id),
    KEY ix_refresh_family (family_id),
    KEY ix_refresh_expires (expires_at),
    CONSTRAINT fk_refresh_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS password_resets (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL,
    token_hash  CHAR(64)        NOT NULL,
    expires_at  TIMESTAMP       NOT NULL,
    used_at     TIMESTAMP       NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pwreset_token (token_hash),
    KEY ix_pwreset_user (user_id),
    CONSTRAINT fk_pwreset_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    actor_id     BIGINT UNSIGNED NULL,                     -- null for system actions
    action       VARCHAR(128)    NOT NULL,                 -- e.g. coupon.update, subscription.cancel
    entity_type  VARCHAR(64)     NULL,
    entity_id    VARCHAR(64)     NULL,
    ip_address   VARBINARY(16)   NULL,
    user_agent   VARCHAR(255)    NULL,
    metadata     JSON            NULL,
    created_at   TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_audit_actor (actor_id),
    KEY ix_audit_action (action),
    KEY ix_audit_entity (entity_type, entity_id),
    KEY ix_audit_created (created_at),
    CONSTRAINT fk_audit_actor FOREIGN KEY (actor_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Merchants, aliases, categories
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS merchants (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    slug          VARCHAR(120)    NOT NULL,                -- nike, amazon, hostinger
    name          VARCHAR(180)    NOT NULL,
    domain        VARCHAR(190)    NULL,
    logo_url      VARCHAR(512)    NULL,
    description   TEXT            NULL,
    trust_score   DECIMAL(4,3)    NOT NULL DEFAULT 0.500,  -- 0..1 baseline source trust
    is_active     TINYINT(1)      NOT NULL DEFAULT 1,
    coupon_count  INT UNSIGNED    NOT NULL DEFAULT 0,       -- denormalized counter
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_merchants_slug (slug),
    KEY ix_merchants_domain (domain),
    KEY ix_merchants_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS merchant_aliases (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    merchant_id BIGINT UNSIGNED NOT NULL,
    alias       VARCHAR(180)    NOT NULL,                  -- "niek", "amzn", common misspellings
    weight      DECIMAL(4,3)    NOT NULL DEFAULT 1.000,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_alias_merchant (merchant_id, alias),
    KEY ix_alias_value (alias),
    CONSTRAINT fk_alias_merchant FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS categories (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    slug        VARCHAR(120)    NOT NULL,
    name        VARCHAR(180)    NOT NULL,
    parent_id   BIGINT UNSIGNED NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_categories_slug (slug),
    KEY ix_categories_parent (parent_id),
    CONSTRAINT fk_categories_parent FOREIGN KEY (parent_id) REFERENCES categories (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Ingestion sources & crawl jobs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    merchant_id     BIGINT UNSIGNED NULL,                  -- may be unknown at discovery
    type            ENUM('merchant_page','promo_page','rss','sitemap','newsletter','user_submission') NOT NULL,
    url             VARCHAR(1024)   NOT NULL,
    url_hash        CHAR(64)        NOT NULL,              -- sha256(url) for unique index
    trust_score     DECIMAL(4,3)    NOT NULL DEFAULT 0.500,
    crawl_frequency INT UNSIGNED    NOT NULL DEFAULT 86400, -- seconds
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    last_crawled_at TIMESTAMP       NULL,
    last_status     VARCHAR(32)     NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sources_url_hash (url_hash),
    KEY ix_sources_merchant (merchant_id),
    KEY ix_sources_type (type),
    KEY ix_sources_active_next (is_active, last_crawled_at),
    CONSTRAINT fk_sources_merchant FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS crawl_jobs (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source_id     BIGINT UNSIGNED NOT NULL,
    status        ENUM('queued','running','succeeded','failed','skipped') NOT NULL DEFAULT 'queued',
    stage         VARCHAR(32)     NULL,                    -- crawl/clean/extract/structure/...
    items_found   INT UNSIGNED    NOT NULL DEFAULT 0,
    items_ingested INT UNSIGNED   NOT NULL DEFAULT 0,
    error         TEXT            NULL,
    started_at    TIMESTAMP       NULL,
    finished_at   TIMESTAMP       NULL,
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_crawl_source (source_id),
    KEY ix_crawl_status (status),
    KEY ix_crawl_created (created_at),
    CONSTRAINT fk_crawl_source FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Coupons (the core entity) + scores + feedback
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coupons (
    id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    uuid               CHAR(36)        NOT NULL,
    merchant_id        BIGINT UNSIGNED NOT NULL,
    source_id          BIGINT UNSIGNED NULL,
    title              VARCHAR(255)    NOT NULL,
    description        TEXT            NULL,
    code               VARCHAR(120)    NULL,               -- NULL = deal without code
    discount_type      ENUM('percentage','fixed','bogo','free_shipping','trial','other') NOT NULL DEFAULT 'other',
    discount_value     DECIMAL(10,2)   NULL,               -- 20 for 20%, 15.00 for $15
    currency           CHAR(3)         NULL,
    landing_url        VARCHAR(1024)   NULL,
    terms              TEXT            NULL,
    content_hash       CHAR(64)        NOT NULL,           -- for dedup (merchant+code+value+title)
    status             ENUM('draft','active','expired','revoked','pending_review') NOT NULL DEFAULT 'pending_review',
    starts_at          TIMESTAMP       NULL,
    expires_at         TIMESTAMP       NULL,
    -- ---- six component scores (0..1) ----
    source_trust_score DECIMAL(4,3)    NOT NULL DEFAULT 0.500,
    freshness_score    DECIMAL(4,3)    NOT NULL DEFAULT 0.500,
    confidence_score   DECIMAL(4,3)    NOT NULL DEFAULT 0.500,
    duplicate_score    DECIMAL(4,3)    NOT NULL DEFAULT 0.000,
    success_rate_score DECIMAL(4,3)    NOT NULL DEFAULT 0.500,
    expiry_score       DECIMAL(4,3)    NOT NULL DEFAULT 0.500,
    ranking_score      DECIMAL(6,4)    NOT NULL DEFAULT 0.5000,  -- final blended score
    -- ---- engagement counters ----
    views              INT UNSIGNED    NOT NULL DEFAULT 0,
    clicks             INT UNSIGNED    NOT NULL DEFAULT 0,
    success_reports    INT UNSIGNED    NOT NULL DEFAULT 0,
    fail_reports       INT UNSIGNED    NOT NULL DEFAULT 0,
    indexed_at         TIMESTAMP       NULL,               -- last pushed to Meilisearch
    created_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_coupons_uuid (uuid),
    UNIQUE KEY uq_coupons_content_hash (content_hash),
    KEY ix_coupons_merchant (merchant_id),
    KEY ix_coupons_source (source_id),
    KEY ix_coupons_status_rank (status, ranking_score),
    KEY ix_coupons_expires (expires_at),
    KEY ix_coupons_status_expires (status, expires_at),
    KEY ix_coupons_indexed (indexed_at),
    CONSTRAINT fk_coupons_merchant FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE CASCADE,
    CONSTRAINT fk_coupons_source FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS coupon_categories (
    coupon_id   BIGINT UNSIGNED NOT NULL,
    category_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (coupon_id, category_id),
    KEY ix_cc_category (category_id),
    CONSTRAINT fk_cc_coupon FOREIGN KEY (coupon_id) REFERENCES coupons (id) ON DELETE CASCADE,
    CONSTRAINT fk_cc_category FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS coupon_validation_events (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    coupon_id   BIGINT UNSIGNED NOT NULL,
    event_type  ENUM('scored','revalidated','expired','flagged','restored') NOT NULL,
    old_score   DECIMAL(6,4)    NULL,
    new_score   DECIMAL(6,4)    NULL,
    detail      JSON            NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_cve_coupon (coupon_id),
    KEY ix_cve_created (created_at),
    CONSTRAINT fk_cve_coupon FOREIGN KEY (coupon_id) REFERENCES coupons (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS coupon_feedback (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    coupon_id   BIGINT UNSIGNED NOT NULL,
    user_id     BIGINT UNSIGNED NULL,
    worked      TINYINT(1)      NOT NULL,                  -- 1 success, 0 fail
    comment     VARCHAR(512)    NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_feedback_coupon (coupon_id),
    KEY ix_feedback_user (user_id),
    CONSTRAINT fk_feedback_coupon FOREIGN KEY (coupon_id) REFERENCES coupons (id) ON DELETE CASCADE,
    CONSTRAINT fk_feedback_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- User features: saved, watchlist, alerts, notifications, referrals
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_coupons (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL,
    coupon_id   BIGINT UNSIGNED NOT NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_saved_user_coupon (user_id, coupon_id),
    KEY ix_saved_coupon (coupon_id),
    CONSTRAINT fk_saved_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_saved_coupon FOREIGN KEY (coupon_id) REFERENCES coupons (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS watchlists (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL,
    merchant_id BIGINT UNSIGNED NOT NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_watch_user_merchant (user_id, merchant_id),
    KEY ix_watch_merchant (merchant_id),
    CONSTRAINT fk_watch_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_watch_merchant FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS deal_alerts (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id       BIGINT UNSIGNED NOT NULL,
    merchant_id   BIGINT UNSIGNED NULL,
    keyword       VARCHAR(190)    NULL,
    min_discount  DECIMAL(10,2)   NULL,
    channel       ENUM('email','push','in_app') NOT NULL DEFAULT 'in_app',
    is_active     TINYINT(1)      NOT NULL DEFAULT 1,
    last_fired_at TIMESTAMP       NULL,
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_alert_user (user_id),
    KEY ix_alert_merchant (merchant_id),
    KEY ix_alert_active (is_active),
    CONSTRAINT fk_alert_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_alert_merchant FOREIGN KEY (merchant_id) REFERENCES merchants (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS notifications (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL,
    type        VARCHAR(64)     NOT NULL,                  -- deal_alert, billing, system
    title       VARCHAR(190)    NOT NULL,
    body        VARCHAR(1024)   NULL,
    data        JSON            NULL,
    read_at     TIMESTAMP       NULL,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_notif_user_read (user_id, read_at),
    KEY ix_notif_created (created_at),
    CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS referrals (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    referrer_id   BIGINT UNSIGNED NOT NULL,
    referred_id   BIGINT UNSIGNED NULL,
    code          VARCHAR(16)     NOT NULL,
    status        ENUM('pending','converted','rewarded') NOT NULL DEFAULT 'pending',
    reward_amount DECIMAL(10,2)   NULL,
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    converted_at  TIMESTAMP       NULL,
    PRIMARY KEY (id),
    KEY ix_ref_referrer (referrer_id),
    KEY ix_ref_referred (referred_id),
    KEY ix_ref_code (code),
    CONSTRAINT fk_ref_referrer FOREIGN KEY (referrer_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_ref_referred FOREIGN KEY (referred_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Search analytics & synonyms
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS search_queries (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id          BIGINT UNSIGNED NULL,
    raw_query        VARCHAR(512)    NOT NULL,
    normalized_query VARCHAR(512)    NULL,
    detected_merchant_id BIGINT UNSIGNED NULL,
    intent           JSON            NULL,                 -- {merchant, time_intent, discount_intent, corrected_q, confidence}
    results_count    INT UNSIGNED    NOT NULL DEFAULT 0,
    latency_ms       INT UNSIGNED    NULL,
    cache_hit        TINYINT(1)      NOT NULL DEFAULT 0,
    ai_provider      VARCHAR(32)     NULL,
    created_at       TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_sq_user (user_id),
    KEY ix_sq_created (created_at),
    KEY ix_sq_merchant (detected_merchant_id),
    CONSTRAINT fk_sq_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_sq_merchant FOREIGN KEY (detected_merchant_id) REFERENCES merchants (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS synonyms (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    term        VARCHAR(120)    NOT NULL,
    synonyms    JSON            NOT NULL,                  -- ["coupon","promo","voucher"]
    is_active   TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_synonyms_term (term)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- Billing: plans, subscriptions, payments, invoices, methods, webhooks
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plans (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    slug            VARCHAR(64)     NOT NULL,              -- free, starter, pro, yearly_pro, yearly_elite
    name            VARCHAR(120)    NOT NULL,
    description     VARCHAR(255)    NULL,
    price_cents     INT UNSIGNED    NOT NULL DEFAULT 0,
    currency        CHAR(3)         NOT NULL DEFAULT 'USD',
    billing_period  ENUM('day','month','year','lifetime','custom') NOT NULL DEFAULT 'month',
    quota_limit     INT UNSIGNED    NOT NULL DEFAULT 10,   -- searches allowed in the window
    quota_window    ENUM('day','month') NOT NULL DEFAULT 'day',
    is_public       TINYINT(1)      NOT NULL DEFAULT 1,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    sort_order      INT             NOT NULL DEFAULT 0,
    stripe_price_id VARCHAR(120)    NULL,
    razorpay_plan_id VARCHAR(120)   NULL,
    metadata        JSON            NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_plans_slug (slug),
    KEY ix_plans_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS subscriptions (
    id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id               BIGINT UNSIGNED NOT NULL,
    plan_id               BIGINT UNSIGNED NOT NULL,
    gateway               ENUM('stripe','razorpay','manual') NOT NULL DEFAULT 'manual',
    gateway_subscription_id VARCHAR(190)  NULL,
    gateway_customer_id   VARCHAR(190)    NULL,
    status                ENUM('trialing','active','past_due','canceled','expired','paused') NOT NULL DEFAULT 'active',
    current_period_start  TIMESTAMP       NULL,
    current_period_end    TIMESTAMP       NULL,
    cancel_at_period_end  TINYINT(1)      NOT NULL DEFAULT 0,
    canceled_at           TIMESTAMP       NULL,
    trial_ends_at         TIMESTAMP       NULL,
    created_at            TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_sub_user (user_id),
    KEY ix_sub_plan (plan_id),
    KEY ix_sub_status (status),
    KEY ix_sub_gateway_id (gateway_subscription_id),
    KEY ix_sub_period_end (current_period_end),
    CONSTRAINT fk_sub_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_sub_plan FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS payment_methods (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id             BIGINT UNSIGNED NOT NULL,
    gateway             ENUM('stripe','razorpay') NOT NULL,
    gateway_method_id   VARCHAR(190)    NOT NULL,
    brand               VARCHAR(40)     NULL,
    last4               CHAR(4)         NULL,
    exp_month           TINYINT UNSIGNED NULL,
    exp_year            SMALLINT UNSIGNED NULL,
    is_default          TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_pm_user (user_id),
    CONSTRAINT fk_pm_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS payments (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id             BIGINT UNSIGNED NOT NULL,
    subscription_id     BIGINT UNSIGNED NULL,
    gateway             ENUM('stripe','razorpay','manual') NOT NULL,
    gateway_payment_id  VARCHAR(190)    NULL,
    amount_cents        INT UNSIGNED    NOT NULL,
    currency            CHAR(3)         NOT NULL DEFAULT 'USD',
    status              ENUM('pending','succeeded','failed','refunded','partially_refunded') NOT NULL DEFAULT 'pending',
    failure_reason      VARCHAR(255)    NULL,
    retry_count         TINYINT UNSIGNED NOT NULL DEFAULT 0,
    next_retry_at       TIMESTAMP       NULL,
    paid_at             TIMESTAMP       NULL,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_pay_user (user_id),
    KEY ix_pay_subscription (subscription_id),
    KEY ix_pay_status (status),
    KEY ix_pay_gateway_id (gateway_payment_id),
    KEY ix_pay_retry (next_retry_at),
    CONSTRAINT fk_pay_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_pay_subscription FOREIGN KEY (subscription_id) REFERENCES subscriptions (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS invoices (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id             BIGINT UNSIGNED NOT NULL,
    subscription_id     BIGINT UNSIGNED NULL,
    payment_id          BIGINT UNSIGNED NULL,
    number              VARCHAR(40)     NOT NULL,          -- INV-2026-000123
    amount_cents        INT UNSIGNED    NOT NULL,
    currency            CHAR(3)         NOT NULL DEFAULT 'USD',
    status              ENUM('draft','open','paid','void','uncollectible') NOT NULL DEFAULT 'open',
    line_items          JSON            NULL,
    pdf_url             VARCHAR(512)    NULL,
    issued_at           TIMESTAMP       NULL,
    due_at              TIMESTAMP       NULL,
    paid_at             TIMESTAMP       NULL,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_invoice_number (number),
    KEY ix_inv_user (user_id),
    KEY ix_inv_subscription (subscription_id),
    KEY ix_inv_status (status),
    CONSTRAINT fk_inv_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_inv_subscription FOREIGN KEY (subscription_id) REFERENCES subscriptions (id) ON DELETE SET NULL,
    CONSTRAINT fk_inv_payment FOREIGN KEY (payment_id) REFERENCES payments (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS webhook_events (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    gateway         ENUM('stripe','razorpay') NOT NULL,
    event_id        VARCHAR(190)    NOT NULL,              -- gateway event id, for idempotency
    event_type      VARCHAR(120)    NOT NULL,
    payload         JSON            NOT NULL,
    status          ENUM('received','processed','failed','ignored') NOT NULL DEFAULT 'received',
    error           TEXT            NULL,
    received_at     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at    TIMESTAMP       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_webhook_gateway_event (gateway, event_id),
    KEY ix_webhook_type (event_type),
    KEY ix_webhook_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- AI providers & usage; feature flags; settings; queue
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_providers (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    slug          VARCHAR(32)     NOT NULL,                -- groq, gemini, openai
    name          VARCHAR(64)     NOT NULL,
    is_enabled    TINYINT(1)      NOT NULL DEFAULT 1,
    priority      INT             NOT NULL DEFAULT 100,    -- lower = tried first
    model         VARCHAR(120)    NULL,
    timeout_s     INT UNSIGNED    NOT NULL DEFAULT 8,
    config        JSON            NULL,
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ai_provider_slug (slug),
    KEY ix_ai_provider_enabled_priority (is_enabled, priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS ai_usage_logs (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    provider      VARCHAR(32)     NOT NULL,
    operation     VARCHAR(64)     NOT NULL,                -- query_understanding, coupon_structuring
    model         VARCHAR(120)    NULL,
    prompt_tokens INT UNSIGNED    NULL,
    output_tokens INT UNSIGNED    NULL,
    latency_ms    INT UNSIGNED    NULL,
    success       TINYINT(1)      NOT NULL DEFAULT 1,
    error         VARCHAR(512)    NULL,
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_ai_usage_provider (provider),
    KEY ix_ai_usage_created (created_at),
    KEY ix_ai_usage_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS feature_flags (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    flag_key      VARCHAR(120)    NOT NULL,
    description   VARCHAR(255)    NULL,
    is_enabled    TINYINT(1)      NOT NULL DEFAULT 0,
    rollout_pct   TINYINT UNSIGNED NOT NULL DEFAULT 100,   -- 0..100
    metadata      JSON            NULL,
    updated_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_flag_key (flag_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS settings (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    setting_key   VARCHAR(120)    NOT NULL,
    value         JSON            NOT NULL,
    description   VARCHAR(255)    NULL,
    updated_by    BIGINT UNSIGNED NULL,
    updated_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_setting_key (setting_key),
    CONSTRAINT fk_setting_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS queue_jobs (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    queue         VARCHAR(64)     NOT NULL DEFAULT 'default',
    job_type      VARCHAR(120)    NOT NULL,
    payload       JSON            NULL,
    status        ENUM('queued','running','succeeded','failed') NOT NULL DEFAULT 'queued',
    attempts      TINYINT UNSIGNED NOT NULL DEFAULT 0,
    max_attempts  TINYINT UNSIGNED NOT NULL DEFAULT 3,
    available_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error         TEXT            NULL,
    created_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_queue_status_available (queue, status, available_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

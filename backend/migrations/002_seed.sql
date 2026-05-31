-- =====================================================================
-- CouponGPT — Seed data (idempotent via INSERT ... ON DUPLICATE KEY)
-- Roles, permissions, plans, AI providers, settings, sample catalog.
-- =====================================================================
SET NAMES utf8mb4;

-- ---- Roles ----
INSERT INTO roles (slug, name, description, is_system) VALUES
  ('super_admin','Super Admin','Full unrestricted access',1),
  ('admin','Admin','Administrative access',1),
  ('operations','Operations','Manage sources, crawlers, coupons',1),
  ('analyst','Analyst','Read-only analytics access',1),
  ('moderator','Moderator','Moderate coupons and submissions',1),
  ('support','Support','Assist users, view billing',1),
  ('user','User','Standard end user',1)
ON DUPLICATE KEY UPDATE name=VALUES(name), description=VALUES(description);

-- ---- Permissions ----
INSERT INTO permissions (slug, name, category) VALUES
  ('dashboard.view','View dashboard','dashboard'),
  ('merchants.read','Read merchants','merchants'),
  ('merchants.write','Manage merchants','merchants'),
  ('sources.read','Read sources','sources'),
  ('sources.write','Manage sources','sources'),
  ('coupons.read','Read coupons','coupons'),
  ('coupons.write','Manage coupons','coupons'),
  ('coupons.moderate','Moderate coupons','coupons'),
  ('validation.run','Run validation/scoring','validation'),
  ('ai.read','View AI center','ai'),
  ('ai.write','Configure AI providers','ai'),
  ('analytics.search','View search analytics','analytics'),
  ('analytics.revenue','View revenue analytics','analytics'),
  ('users.read','Read users','users'),
  ('users.write','Manage users','users'),
  ('subscriptions.read','Read subscriptions','billing'),
  ('subscriptions.write','Manage subscriptions','billing'),
  ('billing.refund','Issue refunds','billing'),
  ('logs.read','View logs/audit','system'),
  ('queues.read','View queues','system'),
  ('queues.write','Manage queues','system'),
  ('crawlers.run','Run crawlers','system'),
  ('flags.write','Manage feature flags','system'),
  ('settings.write','Manage settings','system')
ON DUPLICATE KEY UPDATE name=VALUES(name), category=VALUES(category);

-- super_admin gets every permission
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
WHERE r.slug='super_admin'
ON DUPLICATE KEY UPDATE role_id=role_id;

-- admin gets everything except settings.write/flags.write reserved to super_admin
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
  ON p.slug NOT IN ('settings.write','flags.write','billing.refund')
WHERE r.slug='admin'
ON DUPLICATE KEY UPDATE role_id=role_id;

-- operations
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
  ON p.slug IN ('dashboard.view','merchants.read','merchants.write','sources.read',
                'sources.write','coupons.read','coupons.write','validation.run',
                'crawlers.run','queues.read')
WHERE r.slug='operations'
ON DUPLICATE KEY UPDATE role_id=role_id;

-- analyst
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
  ON p.slug IN ('dashboard.view','analytics.search','analytics.revenue',
                'coupons.read','merchants.read','users.read','subscriptions.read')
WHERE r.slug='analyst'
ON DUPLICATE KEY UPDATE role_id=role_id;

-- moderator
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
  ON p.slug IN ('dashboard.view','coupons.read','coupons.moderate','merchants.read')
WHERE r.slug='moderator'
ON DUPLICATE KEY UPDATE role_id=role_id;

-- support
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
  ON p.slug IN ('dashboard.view','users.read','subscriptions.read','logs.read')
WHERE r.slug='support'
ON DUPLICATE KEY UPDATE role_id=role_id;

-- ---- Subscription plans ----
INSERT INTO plans (slug, name, description, price_cents, currency, billing_period, quota_limit, quota_window, sort_order) VALUES
  ('free','Free','Get started for free',0,'USD','month',10,'day',0),
  ('starter','Starter','For casual deal hunters',500,'USD','month',100,'month',1),
  ('pro','Pro','For power users',1000,'USD','month',200,'month',2),
  ('yearly_pro','Yearly Pro','Best value, daily quota',4900,'USD','year',100,'day',3),
  ('yearly_elite','Yearly Elite','Maximum daily quota',9900,'USD','year',200,'day',4)
ON DUPLICATE KEY UPDATE name=VALUES(name), price_cents=VALUES(price_cents),
  quota_limit=VALUES(quota_limit), quota_window=VALUES(quota_window),
  billing_period=VALUES(billing_period), sort_order=VALUES(sort_order);

-- ---- AI providers (fallback chain priority: groq < gemini < openai) ----
INSERT INTO ai_providers (slug, name, is_enabled, priority, model, timeout_s) VALUES
  ('groq','Groq',1,10,'llama-3.3-70b-versatile',8),
  ('gemini','Google Gemini',1,20,'gemini-1.5-flash',8),
  ('openai','OpenAI',1,30,'gpt-4o-mini',8)
ON DUPLICATE KEY UPDATE name=VALUES(name), priority=VALUES(priority), model=VALUES(model);

-- ---- Ranking weights & system settings ----
INSERT INTO settings (setting_key, value, description) VALUES
  ('ranking_weights',
   JSON_OBJECT('relevance',0.35,'trust',0.15,'freshness',0.15,'confidence',0.10,'success',0.15,'expiry',0.10,'duplicate_penalty',0.20),
   'Weights for the blended coupon ranking score'),
  ('search_defaults',
   JSON_OBJECT('limit',20,'typo_tolerance',true,'cache_ttl_seconds',300),
   'Default search parameters'),
  ('ingestion_defaults',
   JSON_OBJECT('default_crawl_frequency',86400,'max_items_per_source',500),
   'Default ingestion parameters')
ON DUPLICATE KEY UPDATE value=VALUES(value);

-- ---- Feature flags ----
INSERT INTO feature_flags (flag_key, description, is_enabled, rollout_pct) VALUES
  ('ai_query_understanding','Use AI to parse search intent',1,100),
  ('user_submissions','Allow users to submit coupons',1,100),
  ('deal_alerts','Enable deal alert delivery',1,100),
  ('referrals','Enable referral program',1,100)
ON DUPLICATE KEY UPDATE description=VALUES(description);

-- ---- Synonyms for the search engine ----
INSERT INTO synonyms (term, synonyms) VALUES
  ('coupon', JSON_ARRAY('coupon','coupons','promo','promo code','voucher','discount code','deal','offer')),
  ('discount', JSON_ARRAY('discount','off','sale','savings','deal')),
  ('free shipping', JSON_ARRAY('free shipping','free delivery','no shipping fee'))
ON DUPLICATE KEY UPDATE synonyms=VALUES(synonyms);

-- ---- Sample merchants ----
INSERT INTO merchants (slug, name, domain, trust_score) VALUES
  ('amazon','Amazon','amazon.com',0.950),
  ('nike','Nike','nike.com',0.930),
  ('hostinger','Hostinger','hostinger.com',0.880),
  ('nordvpn','NordVPN','nordvpn.com',0.870),
  ('adidas','Adidas','adidas.com',0.910)
ON DUPLICATE KEY UPDATE name=VALUES(name), domain=VALUES(domain), trust_score=VALUES(trust_score);

-- ---- Merchant aliases (typo / shorthand resilience) ----
INSERT INTO merchant_aliases (merchant_id, alias, weight)
SELECT m.id, a.alias, a.weight FROM merchants m
JOIN (
  SELECT 'amazon' AS slug, 'amzn' AS alias, 0.9 AS weight UNION ALL
  SELECT 'amazon','amazn',0.8 UNION ALL
  SELECT 'amazon','amazone',0.8 UNION ALL
  SELECT 'nike','niek',0.8 UNION ALL
  SELECT 'nike','nik',0.7 UNION ALL
  SELECT 'hostinger','hostingr',0.8 UNION ALL
  SELECT 'hostinger','hostinger.com',0.9 UNION ALL
  SELECT 'nordvpn','nord vpn',0.9 UNION ALL
  SELECT 'nordvpn','nord',0.6 UNION ALL
  SELECT 'adidas','addidas',0.8 UNION ALL
  SELECT 'adidas','adias',0.7
) a ON a.slug = m.slug
ON DUPLICATE KEY UPDATE weight=VALUES(weight);

-- ---- Categories ----
INSERT INTO categories (slug, name) VALUES
  ('electronics','Electronics'),
  ('fashion','Fashion'),
  ('hosting','Web Hosting'),
  ('software','Software & SaaS'),
  ('vpn','VPN & Security')
ON DUPLICATE KEY UPDATE name=VALUES(name);

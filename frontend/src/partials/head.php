<?php
use App\Auth;
use App\Csrf;
use function App\e;

/** Shared <head>. $pageTitle may be set by the including layout. */
$pageTitle = $pageTitle ?? (\App\Config::appName() . ' — AI Coupon Search');
?>
<!doctype html>
<html lang="en" class="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= e($pageTitle) ?></title>
  <meta name="description" content="AI-powered coupon search. Find the best verified coupons, promo codes and deals — instantly.">
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: { extend: {
        colors: {
          bg: '#0B0F19', card: '#121826', accent: '#FF7A18', accent2: '#FF9D4D',
          muted: '#94A3B8',
        },
        fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'] },
        borderRadius: { xl: '1rem', '2xl': '1.25rem' },
      } }
    };
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/app.css">
  <script>
    window.__CGPT__ = {
      csrf: <?= json_encode(Csrf::token()) ?>,
      authed: <?= Auth::check() ? 'true' : 'false' ?>,
      role: <?= json_encode(Auth::role()) ?>,
      commands: [
        { label: 'Home', href: '/', hint: 'go' },
        { label: 'Search coupons', href: '/search', hint: 'go' },
        { label: 'Browse merchants', href: '/merchants', hint: 'go' },
        { label: 'Pricing', href: '/pricing', hint: 'go' },
        <?php if (Auth::check()): ?>
        { label: 'My dashboard', href: '/app', hint: 'go' },
        { label: 'Saved coupons', href: '/app/saved', hint: 'go' },
        { label: 'Billing', href: '/app/billing', hint: 'go' },
        <?php endif; ?>
        <?php if (Auth::isAdmin()): ?>
        { label: 'Admin · Dashboard', href: '/admin', hint: 'admin' },
        { label: 'Admin · Coupons', href: '/admin/coupons', hint: 'admin' },
        { label: 'Admin · AI Center', href: '/admin/ai', hint: 'admin' },
        <?php endif; ?>
      ]
    };
  </script>
  <script defer src="/assets/js/app.js"></script>
</head>

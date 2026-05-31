<?php
use App\Auth;
use function App\e;
use function App\nav_active;
$active = $active ?? '';
$cur = current_path();
$user = Auth::user();
include __DIR__ . '/head.php';

$nav = [
  ['/app', 'Dashboard', 'grid'],
  ['/app/search', 'AI Search', 'search'],
  ['/app/saved', 'Saved Coupons', 'bookmark'],
  ['/app/watchlist', 'Watchlist', 'eye'],
  ['/app/alerts', 'Deal Alerts', 'bell'],
  ['/app/history', 'Search History', 'clock'],
  ['/app/notifications', 'Notifications', 'inbox'],
  ['/app/billing', 'Billing', 'card'],
  ['/app/referrals', 'Referrals', 'gift'],
  ['/app/profile', 'Profile', 'user'],
];
?>
<body class="bg-aurora min-h-screen">
<div class="flex min-h-screen">
  <aside class="hidden lg:flex flex-col w-64 shrink-0 glass border-r border-white/10 p-4">
    <a href="/" class="flex items-center gap-2 font-extrabold text-lg mb-6 px-2">
      <span class="inline-grid place-items-center w-8 h-8 rounded-lg btn-accent">C</span><?= e($appName) ?>
    </a>
    <nav class="space-y-1 flex-1">
      <?php foreach ($nav as [$href, $label]): ?>
        <a href="<?= $href ?>" class="nav-link <?= nav_active($href === '/app' && $cur === '/app' ? '/app' : ($href === '/app' ? '___' : $href), $cur) ?>"><?= e($label) ?></a>
      <?php endforeach; ?>
    </nav>
    <div class="mt-4 card p-3 text-sm">
      <div class="text-white font-medium truncate"><?= e($user['full_name'] ?? $user['email'] ?? 'User') ?></div>
      <div class="text-slate-500 text-xs truncate"><?= e($user['email'] ?? '') ?></div>
      <a href="/logout" class="btn-ghost mt-3 block text-center py-1.5 text-xs">Sign out</a>
    </div>
  </aside>

  <div class="flex-1 min-w-0 flex flex-col">
    <header class="sticky top-0 z-30 glass border-b border-white/10 px-4 h-14 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <a href="/app" class="lg:hidden font-bold"><?= e($appName) ?></a>
        <span class="text-slate-400 text-sm hidden sm:block">Your dashboard</span>
      </div>
      <div class="flex items-center gap-2">
        <button onclick="window.__cmdkOpen && window.__cmdkOpen()" class="btn-ghost px-3 py-1.5 text-xs flex items-center gap-2">Search <kbd class="text-[10px] bg-white/10 px-1.5 py-0.5 rounded">⌘K</kbd></button>
        <?php if (Auth::isAdmin()): ?><a href="/admin" class="btn-ghost px-3 py-1.5 text-xs">Admin</a><?php endif; ?>
      </div>
    </header>
    <main class="p-4 sm:p-6 flex-1 animate-in"><?= $content ?></main>
  </div>
</div>
<?php include __DIR__ . '/flash.php'; ?>
</body>
</html>

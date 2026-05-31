<?php
use App\Auth;
use function App\e;
use function App\nav_active;
$active = $active ?? '';
$cur = current_path();
$user = Auth::user();
include __DIR__ . '/head.php';

$groups = [
  'Overview' => [
    ['/admin', 'Dashboard'],
    ['/admin/analytics', 'Search Analytics'],
    ['/admin/billing', 'Revenue & Billing'],
  ],
  'Catalog' => [
    ['/admin/merchants', 'Merchants'],
    ['/admin/sources', 'Sources'],
    ['/admin/coupons', 'Coupons'],
    ['/admin/validation', 'Validation'],
  ],
  'Intelligence' => [
    ['/admin/ai', 'AI Center'],
    ['/admin/crawlers', 'Crawlers'],
    ['/admin/queues', 'Queues'],
  ],
  'People' => [
    ['/admin/users', 'Users'],
    ['/admin/subscriptions', 'Subscriptions'],
  ],
  'System' => [
    ['/admin/logs', 'Audit Logs'],
    ['/admin/flags', 'Feature Flags'],
    ['/admin/settings', 'Settings'],
  ],
];
?>
<body class="bg-aurora min-h-screen">
<div class="flex min-h-screen">
  <aside class="hidden lg:flex flex-col w-64 shrink-0 glass border-r border-white/10 p-4 overflow-y-auto">
    <a href="/admin" class="flex items-center gap-2 font-extrabold text-lg mb-6 px-2">
      <span class="inline-grid place-items-center w-8 h-8 rounded-lg btn-accent">C</span>
      <span>Mission Control</span>
    </a>
    <nav class="space-y-5 flex-1 text-sm">
      <?php foreach ($groups as $group => $items): ?>
        <div>
          <div class="px-2 mb-1 text-[11px] uppercase tracking-wider text-slate-500"><?= e($group) ?></div>
          <?php foreach ($items as [$href, $label]): ?>
            <?php $isExact = ($href === '/admin'); $isActive = $isExact ? ($cur === '/admin') : str_starts_with($cur, $href); ?>
            <a href="<?= $href ?>" class="nav-link <?= $isActive ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5' ?>"><?= e($label) ?></a>
          <?php endforeach; ?>
        </div>
      <?php endforeach; ?>
    </nav>
    <div class="mt-4 card p-3 text-sm">
      <div class="text-white font-medium truncate"><?= e($user['email'] ?? '') ?></div>
      <div class="badge badge-accent mt-1 inline-block"><?= e(Auth::role()) ?></div>
      <a href="/logout" class="btn-ghost mt-3 block text-center py-1.5 text-xs">Sign out</a>
    </div>
  </aside>

  <div class="flex-1 min-w-0 flex flex-col">
    <header class="sticky top-0 z-30 glass border-b border-white/10 px-4 h-14 flex items-center justify-between">
      <div class="text-sm text-slate-400">Admin / <span class="text-white capitalize"><?= e($active ?: 'dashboard') ?></span></div>
      <div class="flex items-center gap-2">
        <button onclick="window.__cmdkOpen && window.__cmdkOpen()" class="btn-ghost px-3 py-1.5 text-xs flex items-center gap-2">Command <kbd class="text-[10px] bg-white/10 px-1.5 py-0.5 rounded">⌘K</kbd></button>
        <a href="/app" class="btn-ghost px-3 py-1.5 text-xs">User view</a>
      </div>
    </header>
    <main class="p-4 sm:p-6 flex-1 animate-in"><?= $content ?></main>
  </div>
</div>
<?php include __DIR__ . '/flash.php'; ?>
</body>
</html>

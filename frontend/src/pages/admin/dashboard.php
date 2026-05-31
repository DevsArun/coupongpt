<?php
use function App\e;
/** @var ?array $dashboard */
/** @var ?string $error */
$stats = $dashboard['stats'] ?? [];
$top = $dashboard['top_merchants'] ?? [];
$trend = $dashboard['search_trend'] ?? [];

$cards = [
  ['Users', $stats['users_total'] ?? 0, 'total registered'],
  ['Active coupons', $stats['coupons_active'] ?? 0, ($stats['coupons_total'] ?? 0) . ' total'],
  ['Searches today', $stats['searches_today'] ?? 0, ($stats['avg_search_latency_ms'] ?? 0) . 'ms avg'],
  ['Active subs', $stats['active_subscriptions'] ?? 0, 'paying customers'],
  ['Revenue (mo)', money((int)($stats['revenue_month_cents'] ?? 0)), 'this month'],
  ['Pending review', $stats['coupons_pending'] ?? 0, 'coupons awaiting'],
  ['Merchants', $stats['merchants_total'] ?? 0, 'in catalog'],
  ['Sources', $stats['sources_total'] ?? 0, 'ingestion sources'],
];
?>
<div class="flex items-center justify-between mb-6">
  <div>
    <h1 class="text-2xl font-bold">Mission Control</h1>
    <p class="text-slate-400 text-sm">Real-time overview of the platform.</p>
  </div>
  <a href="/admin/coupons" class="btn-accent px-4 py-2 text-sm">Manage coupons</a>
</div>

<?php if (!empty($error)): ?>
  <div class="card p-4 mb-6 border-l-2 border-rose-500 text-sm text-slate-300">
    Couldn't load live data: <?= e($error) ?>. Ensure the backend, MySQL and Redis are running.
  </div>
<?php endif; ?>

<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
  <?php foreach ($cards as [$label, $value, $sub]): ?>
    <div class="card card-hover p-5">
      <div class="text-slate-500 text-xs uppercase tracking-wide"><?= e($label) ?></div>
      <div class="text-2xl font-extrabold mt-2"><?= e((string)$value) ?></div>
      <div class="text-slate-500 text-xs mt-1"><?= e($sub) ?></div>
    </div>
  <?php endforeach; ?>
</div>

<div class="grid lg:grid-cols-3 gap-4 mt-6">
  <div class="card p-5 lg:col-span-2">
    <div class="flex items-center justify-between mb-4">
      <h3 class="font-semibold">Search volume (14 days)</h3>
      <span class="badge badge-accent">live</span>
    </div>
    <div id="trend-chart"></div>
  </div>
  <div class="card p-5">
    <h3 class="font-semibold mb-4">Top merchants</h3>
    <div class="space-y-3">
      <?php if (empty($top)): ?>
        <p class="text-slate-500 text-sm">No data yet.</p>
      <?php else: foreach ($top as $m): ?>
        <div class="flex items-center justify-between text-sm">
          <span class="truncate"><?= e($m['name']) ?></span>
          <span class="text-slate-500"><?= (int)$m['coupon_count'] ?> deals</span>
        </div>
      <?php endforeach; endif; ?>
    </div>
  </div>
</div>

<script>
  document.addEventListener('DOMContentLoaded', function () {
    const trend = <?= json_encode(array_map(fn($t) => (int)($t['count'] ?? 0), $trend)) ?>;
    if (trend.length) window.sparkline(document.getElementById('trend-chart'), trend, { height: 90 });
    else document.getElementById('trend-chart').innerHTML = '<div class="text-slate-600 text-sm py-8 text-center">No search activity yet.</div>';
  });
</script>

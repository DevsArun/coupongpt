<?php
use function App\e;
/** @var string $q */
/** @var array $merchants */
?>
<section class="max-w-7xl mx-auto px-4 pt-12 pb-6">
  <h1 class="text-3xl font-bold">Browse merchants</h1>
  <p class="text-slate-400 mt-2">Explore stores and jump straight to their best verified deals.</p>
  <form action="/merchants" method="get" class="mt-6 max-w-md">
    <div class="card glass p-1.5 flex items-center gap-2">
      <input name="q" value="<?= e($q) ?>" placeholder="Filter merchants…"
        class="flex-1 bg-transparent outline-none px-3 py-2 text-white placeholder:text-slate-500">
      <button class="btn-accent px-4 py-2 text-sm">Filter</button>
    </div>
  </form>
</section>

<section class="max-w-7xl mx-auto px-4 pb-16">
  <?php if (empty($merchants)): ?>
    <div class="text-center py-20 text-slate-400">No merchants found.</div>
  <?php else: ?>
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <?php foreach ($merchants as $m): ?>
        <a href="/search?q=<?= urlencode($m['name'] . ' coupon') ?>" class="card card-hover p-5 flex items-center gap-4">
          <div class="w-12 h-12 rounded-xl glass grid place-items-center font-bold text-lg shrink-0"><?= e(strtoupper(substr($m['name'], 0, 1))) ?></div>
          <div class="min-w-0">
            <div class="font-semibold truncate"><?= e($m['name']) ?></div>
            <div class="text-xs text-slate-500"><?= (int)($m['coupon_count'] ?? 0) ?> deals · trust <?= number_format(((float)($m['trust_score'] ?? 0)) * 100, 0) ?>%</div>
          </div>
        </a>
      <?php endforeach; ?>
    </div>
  <?php endif; ?>
</section>

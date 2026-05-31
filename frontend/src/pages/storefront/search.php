<?php
use function App\e;
/** @var string $q */
/** @var ?array $result */
/** @var bool $ok */
/** @var ?string $error */
$intent = $result['intent'] ?? null;
$results = $result['results'] ?? [];
$latency = $result['latency_ms'] ?? null;
?>
<section class="max-w-7xl mx-auto px-4 pt-10 pb-6">
  <form action="/search" method="get" class="max-w-3xl mx-auto">
    <div class="card glass p-2 flex items-center gap-2">
      <svg class="w-5 h-5 ml-3 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/></svg>
      <input name="q" value="<?= e($q) ?>" autocomplete="off" placeholder="Search any store, deal or promo code…"
        class="flex-1 bg-transparent outline-none px-2 py-3 text-white placeholder:text-slate-500">
      <button class="btn-accent px-5 py-3">Search</button>
    </div>
  </form>
</section>

<section class="max-w-7xl mx-auto px-4 pb-16">
  <?php if ($q === ''): ?>
    <div class="text-center text-slate-400 py-20">
      <p class="text-lg">Try a search like <a class="text-accent2" href="/search?q=best+amazon+coupon+today">best amazon coupon today</a></p>
    </div>
  <?php elseif (!$ok): ?>
    <div class="card p-6 max-w-2xl mx-auto text-center">
      <h3 class="text-lg font-semibold mb-1">We couldn't complete that search</h3>
      <p class="text-slate-400 text-sm"><?= e($error ?? 'Please try again in a moment.') ?></p>
      <?php if (($result['error']['code'] ?? '') === 'quota_exceeded' || str_contains((string)$error, 'quota')): ?>
        <a href="/pricing" class="btn-accent inline-block mt-4 px-4 py-2 text-sm">Upgrade for more searches</a>
      <?php endif; ?>
    </div>
  <?php else: ?>
    <?php if ($intent): ?>
      <div class="flex flex-wrap items-center gap-2 mb-6 text-sm text-slate-400">
        <span>Understood as</span>
        <?php if (!empty($intent['merchant'])): ?>
          <span class="badge badge-accent"><?= e($intent['merchant']) ?></span>
        <?php endif; ?>
        <?php if (!empty($intent['time_intent'])): ?>
          <span class="badge bg-white/5 text-slate-300 border border-white/10"><?= e(str_replace('_', ' ', $intent['time_intent'])) ?></span>
        <?php endif; ?>
        <?php if (!empty($intent['discount_intent']['type']) && $intent['discount_intent']['type'] !== 'any'): ?>
          <span class="badge bg-white/5 text-slate-300 border border-white/10"><?= e($intent['discount_intent']['type']) ?></span>
        <?php endif; ?>
        <?php if (!empty($intent['corrected_query']) && strtolower($intent['corrected_query']) !== strtolower($q)): ?>
          <span class="text-slate-500">· corrected to "<span class="text-slate-300"><?= e($intent['corrected_query']) ?></span>"</span>
        <?php endif; ?>
        <span class="ml-auto text-xs text-slate-600"><?= count($results) ?> results in <?= (int)$latency ?>ms · <?= e($intent['source'] ?? 'heuristic') ?></span>
      </div>
    <?php endif; ?>

    <?php if (empty($results)): ?>
      <div class="text-center py-20 text-slate-400">
        <div class="text-5xl mb-4">🔍</div>
        <p class="text-lg">No live coupons matched "<span class="text-white"><?= e($q) ?></span>".</p>
        <p class="text-sm mt-2">Try a broader term or <a href="/merchants" class="text-accent2">browse merchants</a>.</p>
      </div>
    <?php else: ?>
      <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <?php foreach ($results as $c): ?>
          <?php include __DIR__ . '/../../partials/coupon_card.php'; ?>
        <?php endforeach; ?>
      </div>
    <?php endif; ?>
  <?php endif; ?>
</section>

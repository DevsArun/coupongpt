<?php
use function App\e;
/** @var array $coupon */
$c = $coupon;
$score = (float)($c['ranking_score'] ?? 0);
$hasCode = !empty($c['code']);
?>
<section class="max-w-3xl mx-auto px-4 py-16">
  <a href="/search" class="text-slate-400 text-sm hover:text-white">← Back to search</a>
  <div class="card p-8 mt-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <div class="text-sm text-slate-500">Coupon</div>
        <h1 class="text-2xl font-bold mt-1"><?= e($c['title'] ?? 'Coupon') ?></h1>
      </div>
      <span class="badge badge-accent"><?= e(\discount_label($c)) ?></span>
    </div>

    <?php if (!empty($c['description'])): ?>
      <p class="text-slate-400 mt-4"><?= e($c['description']) ?></p>
    <?php endif; ?>

    <div class="mt-6 flex flex-wrap items-center gap-3">
      <?php if ($hasCode): ?>
        <button onclick="cgptReveal(this, '<?= e($c['uuid']) ?>')" data-code="<?= e($c['code']) ?>"
          class="btn-accent px-6 py-3 font-mono tracking-widest">Reveal code</button>
      <?php endif; ?>
      <a href="/out/<?= e($c['uuid']) ?>" target="_blank" rel="noopener" class="btn-ghost px-6 py-3">Visit store →</a>
    </div>

    <div class="mt-8 grid sm:grid-cols-2 gap-4 text-sm">
      <div class="card p-4">
        <div class="text-slate-500 text-xs mb-2">Quality score</div>
        <div class="score-bar"><span style="width: <?= number_format($score * 100, 0) ?>%"></span></div>
        <div class="text-right text-xs text-slate-500 mt-1"><?= number_format($score * 100, 0) ?>%</div>
      </div>
      <div class="card p-4 space-y-1 text-slate-300">
        <div class="flex justify-between"><span class="text-slate-500">Status</span><span><?= e($c['status'] ?? '—') ?></span></div>
        <div class="flex justify-between"><span class="text-slate-500">Expires</span><span><?= !empty($c['expires_at']) ? e(date('M j, Y', strtotime($c['expires_at']))) : 'No expiry' ?></span></div>
        <div class="flex justify-between"><span class="text-slate-500">Used</span><span><?= (int)($c['clicks'] ?? 0) ?> times</span></div>
      </div>
    </div>

    <div class="mt-6 flex items-center gap-2">
      <span class="text-sm text-slate-400">Did this work?</span>
      <button onclick="cgptFeedback('<?= e($c['uuid']) ?>', true)" class="btn-ghost px-3 py-1.5 text-sm">👍 Yes</button>
      <button onclick="cgptFeedback('<?= e($c['uuid']) ?>', false)" class="btn-ghost px-3 py-1.5 text-sm">👎 No</button>
    </div>
  </div>
</section>

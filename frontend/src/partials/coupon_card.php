<?php
use function App\e;
/**
 * Reusable coupon card. Expects $c (array) with search/result fields.
 * Works for both search results and stored coupons.
 */
$c = $c ?? [];
$score = (float)($c['ranking_score'] ?? 0);
$merchant = $c['merchant_name'] ?? ($c['merchant_slug'] ?? 'Store');
$uuid = $c['uuid'] ?? '';
$hasCode = !empty($c['code']);
?>
<div class="card card-hover p-5 flex flex-col">
  <div class="flex items-start justify-between gap-3">
    <div class="flex items-center gap-3 min-w-0">
      <div class="w-10 h-10 rounded-lg glass grid place-items-center font-bold shrink-0"><?= e(strtoupper(substr($merchant, 0, 1))) ?></div>
      <div class="min-w-0">
        <div class="text-xs text-slate-500 truncate"><?= e($merchant) ?></div>
        <h3 class="font-semibold leading-snug truncate"><?= e($c['title'] ?? 'Coupon') ?></h3>
      </div>
    </div>
    <span class="badge badge-accent shrink-0"><?= e(\discount_label($c)) ?></span>
  </div>

  <?php if (!empty($c['description'])): ?>
    <p class="text-sm text-slate-400 mt-3 line-clamp-2"><?= e(mb_strimwidth($c['description'], 0, 120, '…')) ?></p>
  <?php endif; ?>

  <div class="mt-4 flex items-center gap-2">
    <?php if ($hasCode): ?>
      <button onclick="cgptReveal(this, '<?= e($uuid) ?>')" data-code="<?= e($c['code']) ?>"
        class="btn-accent px-4 py-2 text-sm flex-1 font-mono tracking-wider">Reveal code</button>
    <?php else: ?>
      <a href="/out/<?= e($uuid) ?>" target="_blank" rel="noopener"
        class="btn-accent px-4 py-2 text-sm flex-1 text-center">Get deal</a>
    <?php endif; ?>
    <button onclick="cgptFeedback('<?= e($uuid) ?>', true)" title="Worked" class="btn-ghost px-3 py-2 text-sm">👍</button>
    <button onclick="cgptFeedback('<?= e($uuid) ?>', false)" title="Didn't work" class="btn-ghost px-3 py-2 text-sm">👎</button>
  </div>

  <div class="mt-4 pt-3 border-t border-white/5">
    <div class="flex items-center justify-between text-[11px] text-slate-500 mb-1">
      <span>Quality score</span><span><?= number_format($score * 100, 0) ?>%</span>
    </div>
    <div class="score-bar"><span style="width: <?= number_format($score * 100, 0) ?>%"></span></div>
    <?php if (!empty($c['expires_at'])): ?>
      <div class="text-[11px] text-slate-500 mt-2">Expires <?= e(date('M j, Y', strtotime($c['expires_at']))) ?></div>
    <?php endif; ?>
  </div>
</div>

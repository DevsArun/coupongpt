<?php use function App\e; ?>
<div class="mb-6">
  <h1 class="text-2xl font-bold">Validation engine</h1>
  <p class="text-slate-400 text-sm">Re-score coupons and inspect the six-factor quality model.</p>
</div>

<div class="grid sm:grid-cols-3 gap-4 mb-6">
  <button onclick="reindex()" class="card card-hover p-5 text-left">
    <div class="font-semibold">Rebuild search index</div>
    <div class="text-slate-500 text-sm mt-1">Push all active coupons to Meilisearch.</div>
  </button>
  <button onclick="expireStale()" class="card card-hover p-5 text-left">
    <div class="font-semibold">Expire stale</div>
    <div class="text-slate-500 text-sm mt-1">Mark past-expiry coupons as expired.</div>
  </button>
  <a href="/admin/coupons?status=pending_review" class="card card-hover p-5 block">
    <div class="font-semibold">Review queue</div>
    <div class="text-slate-500 text-sm mt-1">Moderate user-submitted coupons.</div>
  </a>
</div>

<div class="card p-6">
  <h3 class="font-semibold mb-4">The six component scores</h3>
  <div class="grid sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
    <?php
    $factors = [
      ['Source trust', 'How trustworthy the origin merchant/source is.'],
      ['Freshness', 'Exponential decay on how recently the coupon was seen.'],
      ['Confidence', 'Extraction/AI confidence that this is a real, valid coupon.'],
      ['Success rate', 'Wilson-smoothed ratio of "worked" vs "did not work" reports.'],
      ['Expiry', 'Time-to-expiry desirability (expired = 0).'],
      ['Duplicate penalty', 'Penalizes near-duplicate coupons within a merchant.'],
    ];
    foreach ($factors as [$n, $d]): ?>
      <div class="flex gap-3">
        <span class="badge badge-accent shrink-0 mt-0.5"><?= e($n) ?></span>
        <span class="text-slate-400"><?= e($d) ?></span>
      </div>
    <?php endforeach; ?>
  </div>
  <p class="text-slate-500 text-xs mt-5">Final ranking blends these with query-time relevance. Weights are tunable in <a href="/admin/settings" class="text-accent2">Settings → ranking_weights</a>. We never rank by date alone.</p>
</div>

<script>
async function reindex() { try { const r = await cgptApi('/admin/coupons/reindex', { method: 'POST' }); toast(r.message, 'success'); } catch (e) { toast(e.message, 'error'); } }
async function expireStale() { try { const r = await cgptApi('/admin/coupons/expire-stale', { method: 'POST' }); toast(r.message, 'success'); } catch (e) { toast(e.message, 'error'); } }
</script>

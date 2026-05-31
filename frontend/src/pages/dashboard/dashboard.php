<?php
use App\Auth;
use function App\e;
/** @var ?array $quota */
$user = Auth::user();
$used = $quota['used'] ?? 0;
$limit = $quota['limit'] ?? 10;
$remaining = $quota['remaining'] ?? $limit;
$pct = $limit > 0 ? min(100, round($used / $limit * 100)) : 0;
?>
<div class="mb-6">
  <h1 class="text-2xl font-bold">Welcome back, <?= e(explode(' ', $user['full_name'] ?? $user['email'] ?? 'there')[0]) ?> 👋</h1>
  <p class="text-slate-400 text-sm">Here's your snapshot.</p>
</div>

<div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
  <div class="card p-5">
    <div class="text-slate-500 text-xs uppercase">Plan</div>
    <div class="text-xl font-extrabold mt-2 capitalize"><?= e($quota['plan'] ?? 'free') ?></div>
    <a href="/app/billing" class="text-accent2 text-xs hover:underline">Manage →</a>
  </div>
  <div class="card p-5 sm:col-span-2">
    <div class="flex items-center justify-between text-sm">
      <span class="text-slate-500 text-xs uppercase">Search quota (<?= e($quota['window'] ?? 'day') ?>)</span>
      <span class="text-slate-400"><?= (int)$used ?> / <?= (int)$limit ?></span>
    </div>
    <div class="score-bar mt-3"><span style="width: <?= $pct ?>%"></span></div>
    <div class="text-xs text-slate-500 mt-2"><?= (int)$remaining ?> searches remaining</div>
  </div>
  <div class="card p-5 flex flex-col justify-between">
    <div class="text-slate-500 text-xs uppercase">Quick search</div>
    <a href="/app/search" class="btn-accent text-center py-2 text-sm mt-2">New AI search</a>
  </div>
</div>

<div class="grid lg:grid-cols-3 gap-4 mt-6">
  <a href="/app/saved" class="card card-hover p-6"><div class="text-2xl mb-2">🔖</div><div class="font-semibold">Saved coupons</div><p class="text-slate-400 text-sm mt-1">Your stash of deals.</p></a>
  <a href="/app/watchlist" class="card card-hover p-6"><div class="text-2xl mb-2">👁️</div><div class="font-semibold">Watchlist</div><p class="text-slate-400 text-sm mt-1">Track favorite stores.</p></a>
  <a href="/app/alerts" class="card card-hover p-6"><div class="text-2xl mb-2">🔔</div><div class="font-semibold">Deal alerts</div><p class="text-slate-400 text-sm mt-1">Get notified on new deals.</p></a>
</div>

<div class="card p-6 mt-6">
  <h3 class="font-semibold mb-4">Recommended for you</h3>
  <div id="reco" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
</div>

<script>
async function loadReco() {
  try {
    const res = await cgptApi('/search', { query: { q: 'best deals today', limit: 6 } });
    const box = document.getElementById('reco');
    const items = res.results || [];
    if (!items.length) { box.innerHTML = '<p class="text-slate-500 text-sm">Run a search to get recommendations.</p>'; return; }
    box.innerHTML = items.map(c => `
      <div class="card p-4">
        <div class="text-xs text-slate-500">${esc(c.merchant_name)}</div>
        <div class="font-medium text-sm mt-1 truncate">${esc(c.title)}</div>
        <div class="flex items-center justify-between mt-3">
          <span class="badge badge-accent">${esc((c.discount_type||'deal').replace('_',' '))}</span>
          <a href="/out/${esc(c.uuid)}" target="_blank" class="text-accent2 text-xs">Get →</a>
        </div>
      </div>`).join('');
  } catch (e) { document.getElementById('reco').innerHTML = '<p class="text-slate-500 text-sm">Could not load recommendations.</p>'; }
}
document.addEventListener('DOMContentLoaded', loadReco);
</script>

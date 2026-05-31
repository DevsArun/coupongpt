<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Saved coupons</h1><p class="text-slate-400 text-sm">Your hand-picked stash.</p></div>
<div id="list" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
<script>
async function load() {
  try {
    const items = await cgptApi('/me/saved');
    const box = document.getElementById('list');
    if (!items.length) { box.innerHTML = '<div class="col-span-full text-center text-slate-500 py-16">No saved coupons yet. <a href="/app/search" class="text-accent2">Find some →</a></div>'; return; }
    box.innerHTML = items.map(c => {
      const label = (c.discount_type==='percentage'&&c.discount_value)?c.discount_value+'% OFF':(c.discount_type||'deal').replace('_',' ').toUpperCase();
      return `<div class="card card-hover p-5">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0"><div class="text-xs text-slate-500">${esc(c.merchant_name)}</div><h3 class="font-semibold truncate">${esc(c.title)}</h3></div>
          <span class="badge badge-accent shrink-0">${esc(label)}</span></div>
        <div class="mt-4 flex gap-2">
          <a href="/out/${esc(c.coupon_uuid)}" target="_blank" class="btn-accent px-4 py-2 text-sm flex-1 text-center">${c.code?'Use '+esc(c.code):'Get deal'}</a>
          <button onclick="unsave('${esc(c.coupon_uuid)}')" class="btn-ghost px-3 py-2 text-sm">Remove</button></div>
      </div>`;
    }).join('');
  } catch (e) { toast(e.message, 'error'); }
}
async function unsave(uuid) {
  try { await cgptApi('/me/saved/' + encodeURIComponent(uuid), { method: 'DELETE' }); toast('Removed', 'info'); load(); }
  catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

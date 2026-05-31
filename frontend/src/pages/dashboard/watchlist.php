<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Watchlist</h1><p class="text-slate-400 text-sm">Stores you're tracking. Add a merchant by ID or browse the catalog.</p></div>

<div class="card p-4 mb-6 flex flex-wrap items-end gap-3">
  <div><label class="text-xs text-slate-500">Merchant ID</label>
    <input id="m-id" type="number" class="block mt-1 card bg-black/20 px-3 py-2 outline-none text-sm" placeholder="e.g. 2"></div>
  <button onclick="add()" class="btn-accent px-4 py-2 text-sm">Add to watchlist</button>
  <a href="/merchants" class="btn-ghost px-4 py-2 text-sm">Browse merchants</a>
</div>

<div id="list" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
<script>
async function load() {
  try {
    const items = await cgptApi('/me/watchlist');
    const box = document.getElementById('list');
    if (!items.length) { box.innerHTML = '<div class="col-span-full text-center text-slate-500 py-16">Your watchlist is empty.</div>'; return; }
    box.innerHTML = items.map(w => `
      <div class="card card-hover p-5 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg glass grid place-items-center font-bold">${esc(w.merchant_name.charAt(0).toUpperCase())}</div>
          <div><div class="font-semibold">${esc(w.merchant_name)}</div>
          <a href="/search?q=${encodeURIComponent(w.merchant_name+' coupon')}" class="text-accent2 text-xs">View deals →</a></div>
        </div>
        <button onclick="rm(${w.id})" class="btn-ghost px-3 py-1.5 text-xs">Remove</button>
      </div>`).join('');
  } catch (e) { toast(e.message, 'error'); }
}
async function add() {
  const id = parseInt(document.getElementById('m-id').value);
  if (!id) { toast('Enter a merchant ID', 'error'); return; }
  try { await cgptApi('/me/watchlist', { method: 'POST', body: { merchant_id: id } }); toast('Added', 'success'); load(); }
  catch (e) { toast(e.message, 'error'); }
}
async function rm(id) { try { await cgptApi('/me/watchlist/' + id, { method: 'DELETE' }); toast('Removed', 'info'); load(); } catch (e) { toast(e.message, 'error'); } }
document.addEventListener('DOMContentLoaded', load);
</script>

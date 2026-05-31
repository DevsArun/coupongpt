<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Deal alerts</h1><p class="text-slate-400 text-sm">Get notified when matching deals land.</p></div>

<div class="card p-4 mb-6 grid sm:grid-cols-4 gap-3 items-end">
  <div><label class="text-xs text-slate-500">Keyword</label>
    <input id="a-kw" class="block mt-1 card bg-black/20 px-3 py-2 outline-none text-sm w-full" placeholder="e.g. vpn"></div>
  <div><label class="text-xs text-slate-500">Merchant ID (optional)</label>
    <input id="a-m" type="number" class="block mt-1 card bg-black/20 px-3 py-2 outline-none text-sm w-full"></div>
  <div><label class="text-xs text-slate-500">Min discount</label>
    <input id="a-min" type="number" class="block mt-1 card bg-black/20 px-3 py-2 outline-none text-sm w-full" placeholder="e.g. 20"></div>
  <button onclick="add()" class="btn-accent px-4 py-2 text-sm">Create alert</button>
</div>

<div id="list" class="space-y-3"></div>
<script>
async function load() {
  try {
    const items = await cgptApi('/me/alerts');
    const box = document.getElementById('list');
    if (!items.length) { box.innerHTML = '<div class="text-center text-slate-500 py-12">No alerts yet.</div>'; return; }
    box.innerHTML = items.map(a => `
      <div class="card p-4 flex items-center justify-between">
        <div><div class="font-medium">${esc(a.keyword || ('Merchant #' + a.merchant_id))}</div>
        <div class="text-xs text-slate-500">${a.min_discount ? 'min '+a.min_discount+'% · ' : ''}${esc(a.channel)}</div></div>
        <button onclick="rm(${a.id})" class="btn-ghost px-3 py-1.5 text-xs">Delete</button>
      </div>`).join('');
  } catch (e) { toast(e.message, 'error'); }
}
async function add() {
  const body = {
    keyword: document.getElementById('a-kw').value || null,
    merchant_id: parseInt(document.getElementById('a-m').value) || null,
    min_discount: parseFloat(document.getElementById('a-min').value) || null,
    channel: 'in_app',
  };
  try { await cgptApi('/me/alerts', { method: 'POST', body }); toast('Alert created', 'success'); load(); }
  catch (e) { toast(e.message, 'error'); }
}
async function rm(id) { try { await cgptApi('/me/alerts/' + id, { method: 'DELETE' }); toast('Deleted', 'info'); load(); } catch (e) { toast(e.message, 'error'); } }
document.addEventListener('DOMContentLoaded', load);
</script>

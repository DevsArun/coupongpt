<?php use function App\e; ?>
<div class="flex items-center justify-between mb-6">
  <div><h1 class="text-2xl font-bold">Sources</h1><p class="text-slate-400 text-sm">Coupon discovery sources for the ingestion pipeline.</p></div>
  <button onclick="document.getElementById('new-source').classList.toggle('hidden')" class="btn-accent px-4 py-2 text-sm">+ Add source</button>
</div>

<div id="new-source" class="card p-5 mb-6 hidden">
  <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
    <input id="s-url" placeholder="https://store.com/coupons" class="card bg-black/20 px-3 py-2 outline-none text-sm lg:col-span-2">
    <select id="s-type" class="card bg-black/20 px-3 py-2 outline-none text-sm">
      <option value="merchant_page">merchant_page</option>
      <option value="promo_page">promo_page</option>
      <option value="rss">rss</option>
      <option value="sitemap">sitemap</option>
      <option value="newsletter">newsletter</option>
    </select>
    <input id="s-merchant" type="number" placeholder="merchant id (optional)" class="card bg-black/20 px-3 py-2 outline-none text-sm">
  </div>
  <button onclick="createSource()" class="btn-accent px-4 py-2 text-sm mt-3">Add</button>
</div>

<div id="table"></div>

<script>
async function load() {
  try {
    const res = await cgptApi('/admin/sources', { query: { page_size: 100 } });
    renderTable('#table', [
      { key: 'url', label: 'URL', render: r => `<div class="truncate max-w-md">${esc(r.url)}</div>` },
      { key: 'type', label: 'Type' },
      { key: 'trust_score', label: 'Trust', render: r => Math.round((r.trust_score||0)*100)+'%' },
      { key: 'last_status', label: 'Last status', render: r => statusPill(r.last_status || 'queued') },
      { key: 'actions', label: '', render: r => `<button onclick="runSource(${r.id})" class="btn-ghost px-3 py-1 text-xs">Run now</button>` },
    ], res.items || []);
  } catch (e) { toast(e.message, 'error'); }
}
async function createSource() {
  try {
    await cgptApi('/admin/sources', { method: 'POST', body: {
      url: document.getElementById('s-url').value,
      type: document.getElementById('s-type').value,
      merchant_id: parseInt(document.getElementById('s-merchant').value) || null,
    }});
    toast('Source added', 'success');
    document.getElementById('new-source').classList.add('hidden');
    load();
  } catch (e) { toast(e.message, 'error'); }
}
async function runSource(id) {
  toast('Running pipeline…', 'info');
  try {
    const job = await cgptApi('/admin/sources/' + id + '/run', { method: 'POST' });
    toast(`Done: ${job.items_ingested} ingested of ${job.items_found} found`, 'success');
    load();
  } catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

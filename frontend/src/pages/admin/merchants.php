<?php use function App\e; ?>
<div class="flex items-center justify-between mb-6">
  <div><h1 class="text-2xl font-bold">Merchants</h1><p class="text-slate-400 text-sm">Manage stores, trust scores, and aliases.</p></div>
  <button onclick="document.getElementById('new-merchant').classList.toggle('hidden')" class="btn-accent px-4 py-2 text-sm">+ New merchant</button>
</div>

<div id="new-merchant" class="card p-5 mb-6 hidden">
  <h3 class="font-semibold mb-3">Create merchant</h3>
  <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
    <input id="m-name" placeholder="Name" class="card bg-black/20 px-3 py-2 outline-none text-sm">
    <input id="m-slug" placeholder="slug (e.g. nike)" class="card bg-black/20 px-3 py-2 outline-none text-sm">
    <input id="m-domain" placeholder="domain.com" class="card bg-black/20 px-3 py-2 outline-none text-sm">
    <input id="m-trust" type="number" step="0.01" min="0" max="1" value="0.7" placeholder="trust 0-1" class="card bg-black/20 px-3 py-2 outline-none text-sm">
  </div>
  <button onclick="createMerchant()" class="btn-accent px-4 py-2 text-sm mt-3">Create</button>
</div>

<div id="table"></div>

<script>
async function load() {
  try {
    const res = await cgptApi('/admin/merchants', { query: { page_size: 100 } });
    renderTable('#table', [
      { key: 'name', label: 'Merchant', render: r => `<div class="font-medium">${esc(r.name)}</div><div class="text-xs text-slate-500">${esc(r.slug)}</div>` },
      { key: 'domain', label: 'Domain', render: r => esc(r.domain || '—') },
      { key: 'coupon_count', label: 'Coupons' },
      { key: 'trust_score', label: 'Trust', render: r => Math.round((r.trust_score||0)*100) + '%' },
      { key: 'is_active', label: 'Status', render: r => statusPill(r.is_active ? 'active' : 'inactive') },
    ], res.items || []);
  } catch (e) { toast(e.message, 'error'); }
}
async function createMerchant() {
  try {
    await cgptApi('/admin/merchants', { method: 'POST', body: {
      name: document.getElementById('m-name').value,
      slug: document.getElementById('m-slug').value,
      domain: document.getElementById('m-domain').value || null,
      trust_score: parseFloat(document.getElementById('m-trust').value) || 0.5,
    }});
    toast('Merchant created', 'success');
    document.getElementById('new-merchant').classList.add('hidden');
    load();
  } catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

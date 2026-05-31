<?php use function App\e; ?>
<div class="flex items-center justify-between mb-6">
  <div><h1 class="text-2xl font-bold">Coupons</h1><p class="text-slate-400 text-sm">Moderate, edit, and re-score coupons.</p></div>
  <div class="flex gap-2">
    <button onclick="reindex()" class="btn-ghost px-4 py-2 text-sm">Reindex all</button>
    <button onclick="expireStale()" class="btn-ghost px-4 py-2 text-sm">Expire stale</button>
  </div>
</div>

<div class="flex flex-wrap gap-2 mb-4">
  <select id="f-status" onchange="load()" class="card bg-black/20 px-3 py-2 outline-none text-sm">
    <option value="">All statuses</option>
    <option value="active">active</option>
    <option value="pending_review">pending_review</option>
    <option value="expired">expired</option>
    <option value="revoked">revoked</option>
  </select>
  <input id="f-q" oninput="debouncedLoad()" placeholder="Search title…" class="card bg-black/20 px-3 py-2 outline-none text-sm">
</div>

<div id="table"></div>

<script>
let t = null;
function debouncedLoad() { clearTimeout(t); t = setTimeout(load, 300); }
async function load() {
  try {
    const res = await cgptApi('/admin/coupons', { query: {
      status: document.getElementById('f-status').value,
      q: document.getElementById('f-q').value, page_size: 50,
    }});
    renderTable('#table', [
      { key: 'title', label: 'Coupon', render: r => `<div class="font-medium truncate max-w-xs">${esc(r.title)}</div><div class="text-xs text-slate-500">${esc(r.code||'no code')}</div>` },
      { key: 'discount', label: 'Discount', render: r => esc((r.discount_type||'').replace('_',' ')) + (r.discount_value? ' '+r.discount_value : '') },
      { key: 'ranking_score', label: 'Score', render: r => Math.round((r.ranking_score||0)*100)+'%' },
      { key: 'status', label: 'Status', render: r => statusPill(r.status) },
      { key: 'actions', label: 'Actions', render: r => {
        let b = '';
        if (r.status === 'pending_review') b += `<button onclick="moderate(${r.id},'approve')" class="btn-ghost px-2 py-1 text-xs mr-1">Approve</button>`;
        b += `<button onclick="moderate(${r.id},'reject')" class="btn-ghost px-2 py-1 text-xs mr-1">Reject</button>`;
        b += `<button onclick="rescore(${r.id})" class="btn-ghost px-2 py-1 text-xs">Re-score</button>`;
        return b;
      }},
    ], res.items || []);
  } catch (e) { toast(e.message, 'error'); }
}
async function moderate(id, action) {
  try { await cgptApi('/admin/coupons/'+id+'/moderate', { method: 'POST', query: { action } }); toast('Coupon '+action+'d', 'success'); load(); }
  catch (e) { toast(e.message, 'error'); }
}
async function rescore(id) {
  try { await cgptApi('/admin/coupons/'+id+'/rescore', { method: 'POST' }); toast('Re-scored', 'success'); load(); }
  catch (e) { toast(e.message, 'error'); }
}
async function reindex() {
  try { const r = await cgptApi('/admin/coupons/reindex', { method: 'POST' }); toast(r.message, 'success'); }
  catch (e) { toast(e.message, 'error'); }
}
async function expireStale() {
  try { const r = await cgptApi('/admin/coupons/expire-stale', { method: 'POST' }); toast(r.message, 'success'); load(); }
  catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

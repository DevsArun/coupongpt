<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Subscriptions</h1><p class="text-slate-400 text-sm">All customer subscriptions.</p></div>
<div class="flex gap-2 mb-4">
  <select id="f-status" onchange="load()" class="card bg-black/20 px-3 py-2 outline-none text-sm">
    <option value="">All</option><option value="active">active</option><option value="canceled">canceled</option><option value="past_due">past_due</option>
  </select>
</div>
<div id="table"></div>
<script>
async function load() {
  try {
    const res = await cgptApi('/admin/subscriptions', { query: { status: document.getElementById('f-status').value, page_size: 50 }});
    renderTable('#table', [
      { key: 'id', label: 'ID' },
      { key: 'user_id', label: 'User' },
      { key: 'plan', label: 'Plan', render: r => `<span class="badge badge-accent">${esc(r.plan||'—')}</span>` },
      { key: 'gateway', label: 'Gateway' },
      { key: 'status', label: 'Status', render: r => statusPill(r.status) },
      { key: 'current_period_end', label: 'Renews', render: r => esc((r.current_period_end||'—').slice(0,10)) },
    ], res.items || []);
  } catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

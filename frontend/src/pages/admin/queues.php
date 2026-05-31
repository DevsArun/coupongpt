<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Queues</h1><p class="text-slate-400 text-sm">Background job status.</p></div>
<div id="summary" class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6"></div>
<div id="table"></div>
<script>
async function load() {
  try {
    const res = await cgptApi('/admin/queues');
    const s = res.summary || {};
    document.getElementById('summary').innerHTML = ['queued','running','succeeded','failed'].map(k =>
      `<div class="card p-4"><div class="text-slate-500 text-xs uppercase">${k}</div><div class="text-2xl font-extrabold mt-1">${s[k]||0}</div></div>`).join('');
    renderTable('#table', [
      { key: 'id', label: 'ID' }, { key: 'queue', label: 'Queue' }, { key: 'type', label: 'Type' },
      { key: 'attempts', label: 'Attempts' }, { key: 'status', label: 'Status', render: r => statusPill(r.status) },
    ], res.jobs || [], { empty: 'Queue is empty.' });
  } catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

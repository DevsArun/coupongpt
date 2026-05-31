<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Audit logs</h1><p class="text-slate-400 text-sm">Security-relevant and privileged actions.</p></div>
<div id="table"></div>
<script>
async function load() {
  try {
    const res = await cgptApi('/admin/logs', { query: { page_size: 100 } });
    renderTable('#table', [
      { key: 'created_at', label: 'When', render: r => esc(r.created_at) },
      { key: 'action', label: 'Action', render: r => `<span class="badge bg-white/5 text-slate-300 border border-white/10">${esc(r.action)}</span>` },
      { key: 'actor_id', label: 'Actor', render: r => r.actor_id || 'system' },
      { key: 'entity', label: 'Entity', render: r => esc((r.entity_type||'') + (r.entity_id? ' #'+r.entity_id : '')) },
      { key: 'ip_address', label: 'IP', render: r => esc(r.ip_address || '—') },
    ], res.items || [], { empty: 'No audit entries yet.' });
  } catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

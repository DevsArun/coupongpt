<?php use function App\e; ?>
<div class="mb-6">
  <h1 class="text-2xl font-bold">Crawlers</h1>
  <p class="text-slate-400 text-sm">Recent ingestion runs across all sources.</p>
</div>
<div id="table"></div>
<script>
async function load() {
  try {
    const jobs = await cgptApi('/admin/crawl-jobs');
    renderTable('#table', [
      { key: 'id', label: 'Job' },
      { key: 'source_id', label: 'Source' },
      { key: 'stage', label: 'Stage', render: r => esc(r.stage || '—') },
      { key: 'items_found', label: 'Found' },
      { key: 'items_ingested', label: 'Ingested' },
      { key: 'status', label: 'Status', render: r => statusPill(r.status) },
      { key: 'created_at', label: 'When', render: r => esc(r.created_at) },
    ], jobs || [], { empty: 'No crawl jobs yet. Add a source and run it.' });
  } catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Search history</h1><p class="text-slate-400 text-sm">Your recent searches.</p></div>
<div id="table"></div>
<script>
async function load() {
  try {
    const items = await cgptApi('/me/history');
    renderTable('#table', [
      { key: 'raw_query', label: 'Query', render: r => `<a href="/app/search?q=${encodeURIComponent(r.raw_query)}" class="text-accent2">${esc(r.raw_query)}</a>` },
      { key: 'results_count', label: 'Results' },
      { key: 'created_at', label: 'When', render: r => esc(r.created_at) },
    ], items || [], { empty: 'No searches yet. <a href="/app/search" class="text-accent2">Start searching →</a>' });
  } catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

<?php use function App\e; ?>
<div class="mb-6">
  <h1 class="text-2xl font-bold">Search analytics</h1>
  <p class="text-slate-400 text-sm">Demand signals, top queries, and content gaps.</p>
</div>

<div class="card p-5 mb-6">
  <h3 class="font-semibold mb-4">Search volume</h3>
  <div id="trend"></div>
</div>

<div class="grid lg:grid-cols-2 gap-4">
  <div class="card p-5">
    <h3 class="font-semibold mb-3">Top queries</h3>
    <div id="top"></div>
  </div>
  <div class="card p-5">
    <h3 class="font-semibold mb-3">Zero-result queries <span class="text-xs text-slate-500">(content gaps)</span></h3>
    <div id="zero"></div>
  </div>
</div>

<script>
async function load() {
  try {
    const a = await cgptApi('/admin/analytics/search', { query: { days: 14 } });
    const trend = (a.trend || []).map(t => t.count);
    if (trend.length) window.sparkline(document.getElementById('trend'), trend, { height: 100 });
    else document.getElementById('trend').innerHTML = '<div class="text-slate-600 text-sm py-8 text-center">No data yet.</div>';
    renderTable('#top', [
      { key: 'query', label: 'Query' }, { key: 'count', label: 'Count' },
    ], a.top_queries || [], { empty: 'No queries yet.' });
    renderTable('#zero', [
      { key: 'query', label: 'Query' }, { key: 'count', label: 'Count' },
    ], a.zero_result_queries || [], { empty: 'No zero-result queries — nice!' });
  } catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

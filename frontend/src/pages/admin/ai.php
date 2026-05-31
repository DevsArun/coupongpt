<?php use function App\e; ?>
<div class="mb-6">
  <h1 class="text-2xl font-bold">AI Center</h1>
  <p class="text-slate-400 text-sm">Configure the provider fallback chain (Groq → Gemini → OpenAI) and inspect usage.</p>
</div>

<div class="card p-5 mb-6">
  <div class="flex items-center justify-between mb-4">
    <h3 class="font-semibold">Providers</h3>
    <span class="text-xs text-slate-500">Lower priority is tried first. API keys are set via environment variables.</span>
  </div>
  <div id="providers" class="space-y-3"></div>
</div>

<div class="card p-5">
  <h3 class="font-semibold mb-4">Usage (last 7 days)</h3>
  <div id="usage"></div>
</div>

<script>
async function load() {
  try {
    const providers = await cgptApi('/admin/ai/providers');
    document.getElementById('providers').innerHTML = providers.map(p => `
      <div class="flex flex-wrap items-center gap-3 card p-3">
        <div class="font-semibold w-24">${esc(p.name)}</div>
        <label class="flex items-center gap-2 text-sm"><input type="checkbox" ${p.is_enabled?'checked':''} onchange="update('${p.slug}',{is_enabled:this.checked})"> enabled</label>
        <label class="text-sm flex items-center gap-2">priority <input type="number" value="${p.priority}" onchange="update('${p.slug}',{priority:parseInt(this.value)})" class="card bg-black/20 px-2 py-1 w-20 outline-none"></label>
        <label class="text-sm flex items-center gap-2 flex-1 min-w-[12rem]">model <input value="${esc(p.model||'')}" onchange="update('${p.slug}',{model:this.value})" class="card bg-black/20 px-2 py-1 outline-none flex-1"></label>
      </div>`).join('');

    const usage = await cgptApi('/admin/ai/usage', { query: { days: 7 } });
    renderTable('#usage', [
      { key: 'provider', label: 'Provider' },
      { key: 'calls', label: 'Calls' },
      { key: 'successes', label: 'Successes' },
      { key: 'avg_latency_ms', label: 'Avg latency', render: r => (r.avg_latency_ms||0)+'ms' },
    ], usage.providers || [], { empty: 'No AI calls recorded yet. Set provider API keys and run a search.' });
    if (usage.fallback_chain) toast('Fallback chain: ' + usage.fallback_chain.join(' → '), 'info');
  } catch (e) { toast(e.message, 'error'); }
}
async function update(slug, body) {
  try { await cgptApi('/admin/ai/providers/' + slug, { method: 'PATCH', body }); toast('Updated ' + slug, 'success'); }
  catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

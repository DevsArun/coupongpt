<?php use function App\e; ?>
<div class="mb-6">
  <h1 class="text-2xl font-bold">AI Search</h1>
  <p class="text-slate-400 text-sm">Search in plain English — we handle typos, timing, and intent.</p>
</div>

<div class="card glass p-2 flex items-center gap-2 max-w-3xl">
  <svg class="w-5 h-5 ml-3 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/></svg>
  <input id="q" autocomplete="off" placeholder="e.g. bst niek coupn"
    class="flex-1 bg-transparent outline-none px-2 py-3 text-white placeholder:text-slate-500"
    onkeydown="if(event.key==='Enter') runSearch()">
  <button onclick="runSearch()" class="btn-accent px-5 py-3">Search</button>
</div>
<div id="intent" class="mt-4 text-sm text-slate-400"></div>

<div id="results" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6"></div>

<script>
function skeletons(n) {
  return Array.from({length:n}).map(()=>`<div class="card p-5"><div class="skeleton h-5 w-2/3 mb-3"></div><div class="skeleton h-4 w-full mb-2"></div><div class="skeleton h-9 w-full mt-4"></div></div>`).join('');
}
async function runSearch() {
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  const results = document.getElementById('results');
  results.innerHTML = skeletons(6);
  document.getElementById('intent').innerHTML = '';
  try {
    const res = await cgptApi('/search', { query: { q, limit: 24 } });
    const intent = res.intent || {};
    document.getElementById('intent').innerHTML =
      `Understood: ${intent.merchant ? '<span class="badge badge-accent">'+esc(intent.merchant)+'</span> ' : ''}` +
      `${intent.time_intent ? '<span class="badge bg-white/5 border border-white/10 text-slate-300">'+esc(intent.time_intent.replace('_',' '))+'</span> ' : ''}` +
      `<span class="text-slate-600">· ${(res.results||[]).length} results in ${res.latency_ms||0}ms · ${esc(intent.source||'heuristic')}</span>`;
    const items = res.results || [];
    if (!items.length) { results.innerHTML = '<div class="col-span-full text-center text-slate-500 py-12">No coupons matched. Try a broader term.</div>'; return; }
    results.innerHTML = items.map(renderCard).join('');
  } catch (e) {
    results.innerHTML = '';
    toast(e.message || 'Search failed', 'error');
    if ((e.message||'').toLowerCase().includes('quota')) document.getElementById('intent').innerHTML = '<a href="/app/billing" class="text-accent2">Upgrade for more searches →</a>';
  }
}
function renderCard(c) {
  const pct = Math.round((c.ranking_score||0)*100);
  const label = (c.discount_type==='percentage'&&c.discount_value)?c.discount_value+'% OFF':(c.discount_type||'deal').replace('_',' ').toUpperCase();
  const action = c.code
    ? `<button onclick="cgptReveal(this,'${esc(c.uuid)}')" data-code="${esc(c.code)}" class="btn-accent px-4 py-2 text-sm flex-1 font-mono">Reveal code</button>`
    : `<a href="/out/${esc(c.uuid)}" target="_blank" class="btn-accent px-4 py-2 text-sm flex-1 text-center">Get deal</a>`;
  return `<div class="card card-hover p-5">
    <div class="flex items-start justify-between gap-2">
      <div class="min-w-0"><div class="text-xs text-slate-500 truncate">${esc(c.merchant_name)}</div>
      <h3 class="font-semibold truncate">${esc(c.title)}</h3></div>
      <span class="badge badge-accent shrink-0">${esc(label)}</span>
    </div>
    <div class="mt-4 flex gap-2">${action}
      <button onclick="save('${esc(c.uuid)}')" class="btn-ghost px-3 py-2 text-sm" title="Save">🔖</button></div>
    <div class="mt-4"><div class="score-bar"><span style="width:${pct}%"></span></div>
    <div class="text-right text-[11px] text-slate-500 mt-1">${pct}% quality</div></div>
  </div>`;
}
async function save(uuid) {
  try { await cgptApi('/me/saved', { method: 'POST', body: { coupon_uuid: uuid } }); toast('Saved to your coupons', 'success'); }
  catch (e) { toast(e.message, 'error'); }
}
// run an initial query if ?q= present
const params = new URLSearchParams(location.search);
if (params.get('q')) { document.getElementById('q').value = params.get('q'); document.addEventListener('DOMContentLoaded', runSearch); }
</script>

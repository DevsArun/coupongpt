<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Feature flags</h1><p class="text-slate-400 text-sm">Toggle features and control rollout.</p></div>
<div id="flags" class="space-y-3"></div>
<script>
async function load() {
  try {
    const flags = await cgptApi('/admin/feature-flags');
    document.getElementById('flags').innerHTML = (flags || []).map(f => `
      <div class="card p-4 flex items-center justify-between gap-4">
        <div><div class="font-medium">${esc(f.flag_key)}</div><div class="text-xs text-slate-500">${esc(f.description||'')}</div></div>
        <div class="flex items-center gap-3">
          <label class="text-sm flex items-center gap-2">rollout
            <input type="number" min="0" max="100" value="${f.rollout_pct}" onchange="update('${f.flag_key}',{rollout_pct:parseInt(this.value)})" class="card bg-black/20 px-2 py-1 w-16 outline-none text-sm">%</label>
          <label class="flex items-center gap-2 text-sm"><input type="checkbox" ${f.is_enabled?'checked':''} onchange="update('${f.flag_key}',{is_enabled:this.checked})"> enabled</label>
        </div>
      </div>`).join('') || '<div class="text-slate-500 py-8 text-center">No flags configured.</div>';
  } catch (e) { toast(e.message, 'error'); }
}
async function update(key, body) { try { await cgptApi('/admin/feature-flags/'+key, { method:'PATCH', body }); toast('Updated '+key, 'success'); } catch(e){ toast(e.message,'error'); } }
document.addEventListener('DOMContentLoaded', load);
</script>

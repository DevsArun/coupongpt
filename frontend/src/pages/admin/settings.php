<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Settings</h1><p class="text-slate-400 text-sm">Platform configuration. Edit a value as JSON and save.</p></div>
<div id="settings" class="space-y-4"></div>
<script>
async function load() {
  try {
    const data = await cgptApi('/admin/settings');
    const keys = Object.keys(data);
    document.getElementById('settings').innerHTML = keys.length ? keys.map(k => `
      <div class="card p-5">
        <div class="flex items-center justify-between mb-2">
          <div><div class="font-medium">${esc(k)}</div><div class="text-xs text-slate-500">${esc(data[k].description||'')}</div></div>
          <button onclick="save('${k}')" class="btn-accent px-3 py-1.5 text-xs">Save</button>
        </div>
        <textarea id="set-${k}" rows="4" class="w-full card bg-black/20 px-3 py-2 outline-none text-sm font-mono">${esc(JSON.stringify(data[k].value, null, 2))}</textarea>
      </div>`).join('') : '<div class="text-slate-500 py-8 text-center">No settings.</div>';
  } catch (e) { toast(e.message, 'error'); }
}
async function save(key) {
  let value;
  try { value = JSON.parse(document.getElementById('set-' + key).value); }
  catch (e) { toast('Invalid JSON', 'error'); return; }
  try { await cgptApi('/admin/settings/' + key, { method: 'PUT', body: { value } }); toast('Saved ' + key, 'success'); }
  catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

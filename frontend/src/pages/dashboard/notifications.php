<?php use function App\e; ?>
<div class="flex items-center justify-between mb-6">
  <div><h1 class="text-2xl font-bold">Notifications</h1><p class="text-slate-400 text-sm">Updates, alerts, and account activity.</p></div>
  <button onclick="readAll()" class="btn-ghost px-4 py-2 text-sm">Mark all read</button>
</div>
<div id="list" class="space-y-3"></div>
<script>
async function load() {
  try {
    const items = await cgptApi('/me/notifications');
    const box = document.getElementById('list');
    if (!items.length) { box.innerHTML = '<div class="text-center text-slate-500 py-16">You\'re all caught up. 🎉</div>'; return; }
    box.innerHTML = items.map(n => `
      <div class="card p-4 ${n.read_at ? 'opacity-60' : ''}">
        <div class="flex items-center justify-between">
          <div class="font-medium">${esc(n.title)}</div>
          <span class="text-xs text-slate-500">${esc((n.created_at||'').slice(0,16).replace('T',' '))}</span>
        </div>
        ${n.body ? `<p class="text-slate-400 text-sm mt-1">${esc(n.body)}</p>` : ''}
      </div>`).join('');
  } catch (e) { toast(e.message, 'error'); }
}
async function readAll() { try { await cgptApi('/me/notifications/read-all', { method: 'POST' }); toast('Marked all read', 'info'); load(); } catch (e) { toast(e.message, 'error'); } }
document.addEventListener('DOMContentLoaded', load);
</script>

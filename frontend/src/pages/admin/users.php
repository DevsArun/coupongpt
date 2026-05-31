<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Users</h1><p class="text-slate-400 text-sm">Manage accounts, roles, and status.</p></div>
<div class="flex gap-2 mb-4">
  <input id="f-q" oninput="debouncedLoad()" placeholder="Search email…" class="card bg-black/20 px-3 py-2 outline-none text-sm">
  <select id="f-status" onchange="load()" class="card bg-black/20 px-3 py-2 outline-none text-sm">
    <option value="">All</option><option value="active">active</option><option value="suspended">suspended</option>
  </select>
</div>
<div id="table"></div>
<script>
const ROLES = ['user','support','moderator','analyst','operations','admin','super_admin'];
let t = null; function debouncedLoad(){ clearTimeout(t); t=setTimeout(load,300); }
async function load() {
  try {
    const res = await cgptApi('/admin/users', { query: { q: document.getElementById('f-q').value, status: document.getElementById('f-status').value, page_size: 50 }});
    renderTable('#table', [
      { key: 'email', label: 'Email', render: r => `<div class="font-medium">${esc(r.email)}</div><div class="text-xs text-slate-500">${esc(r.full_name||'')}</div>` },
      { key: 'status', label: 'Status', render: r => statusPill(r.status) },
      { key: 'role', label: 'Role', render: r => `<select onchange="setRole(${r.id}, this.value)" class="card bg-black/20 px-2 py-1 text-xs outline-none">${ROLES.map(x=>`<option value="${x}">${x}</option>`).join('')}</select>` },
      { key: 'created_at', label: 'Joined', render: r => esc((r.created_at||'').slice(0,10)) },
      { key: 'actions', label: '', render: r => `<button onclick="setStatus(${r.id}, '${r.status === 'suspended' ? 'active' : 'suspended'}')" class="btn-ghost px-2 py-1 text-xs">${r.status === 'suspended' ? 'Reactivate' : 'Suspend'}</button>` },
    ], res.items || []);
  } catch (e) { toast(e.message, 'error'); }
}
async function setRole(id, role) { try { await cgptApi('/admin/users/'+id, { method:'PATCH', body:{ role_slug: role }}); toast('Role updated','success'); } catch(e){ toast(e.message,'error'); } }
async function setStatus(id, status) { try { await cgptApi('/admin/users/'+id, { method:'PATCH', body:{ status }}); toast('Status updated','success'); load(); } catch(e){ toast(e.message,'error'); } }
document.addEventListener('DOMContentLoaded', load);
</script>

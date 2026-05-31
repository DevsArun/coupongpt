<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Referrals</h1><p class="text-slate-400 text-sm">Invite friends and earn rewards.</p></div>

<div class="card p-6 mb-6">
  <div class="text-slate-500 text-xs uppercase">Your invite link</div>
  <div class="flex flex-wrap items-center gap-3 mt-2">
    <input id="invite" readonly class="flex-1 min-w-[16rem] card bg-black/20 px-4 py-2.5 outline-none text-sm">
    <button onclick="copyInvite()" class="btn-accent px-4 py-2.5 text-sm">Copy link</button>
  </div>
  <div class="mt-2 text-sm text-slate-400">Your code: <span id="code" class="badge badge-accent">—</span></div>
</div>

<div class="grid grid-cols-3 gap-4">
  <div class="card p-5 text-center"><div class="text-3xl font-extrabold" id="s-total">0</div><div class="text-slate-500 text-xs mt-1">Invited</div></div>
  <div class="card p-5 text-center"><div class="text-3xl font-extrabold" id="s-conv">0</div><div class="text-slate-500 text-xs mt-1">Converted</div></div>
  <div class="card p-5 text-center"><div class="text-3xl font-extrabold" id="s-rew">0</div><div class="text-slate-500 text-xs mt-1">Rewarded</div></div>
</div>

<script>
async function load() {
  try {
    const r = await cgptApi('/me/referrals');
    document.getElementById('invite').value = r.invite_url || (location.origin + '/register?ref=' + (r.referral_code||''));
    document.getElementById('code').textContent = r.referral_code || '—';
    document.getElementById('s-total').textContent = r.total || 0;
    document.getElementById('s-conv').textContent = r.converted || 0;
    document.getElementById('s-rew').textContent = r.rewarded || 0;
  } catch (e) { toast(e.message, 'error'); }
}
function copyInvite() { const el = document.getElementById('invite'); el.select(); navigator.clipboard && navigator.clipboard.writeText(el.value); toast('Invite link copied!', 'success'); }
document.addEventListener('DOMContentLoaded', load);
</script>

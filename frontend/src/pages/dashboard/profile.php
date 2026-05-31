<?php
use App\Auth;
use App\Csrf;
use function App\e;
/** @var ?array $me */
$me = $me ?? Auth::user();
?>
<div class="mb-6"><h1 class="text-2xl font-bold">Profile</h1><p class="text-slate-400 text-sm">Your account details.</p></div>

<div class="grid lg:grid-cols-2 gap-4">
  <div class="card p-6">
    <h3 class="font-semibold mb-4">Personal info</h3>
    <form method="post" action="/app/profile" class="space-y-4">
      <?= Csrf::field() ?>
      <div>
        <label class="text-sm text-slate-400">Email</label>
        <input value="<?= e($me['email'] ?? '') ?>" disabled
          class="mt-1 w-full card bg-black/20 px-4 py-2.5 outline-none text-slate-500">
      </div>
      <div>
        <label class="text-sm text-slate-400">Full name</label>
        <input name="full_name" value="<?= e($me['full_name'] ?? '') ?>"
          class="mt-1 w-full card bg-black/20 px-4 py-2.5 outline-none focus:ring-2 focus:ring-accent">
      </div>
      <div>
        <label class="text-sm text-slate-400">Timezone</label>
        <input name="timezone" value="<?= e($me['timezone'] ?? 'UTC') ?>"
          class="mt-1 w-full card bg-black/20 px-4 py-2.5 outline-none focus:ring-2 focus:ring-accent">
      </div>
      <button class="btn-accent px-5 py-2.5 text-sm">Save changes</button>
    </form>
  </div>

  <div class="card p-6">
    <h3 class="font-semibold mb-4">Security</h3>
    <div class="space-y-3 text-sm">
      <div class="flex justify-between"><span class="text-slate-400">Role</span><span class="badge badge-accent"><?= e($me['role'] ?? 'user') ?></span></div>
      <div class="flex justify-between"><span class="text-slate-400">Status</span><span class="capitalize"><?= e($me['status'] ?? 'active') ?></span></div>
      <div class="flex justify-between"><span class="text-slate-400">Member since</span><span><?= e(date('M Y', strtotime($me['created_at'] ?? 'now'))) ?></span></div>
    </div>
    <button onclick="changePw()" class="btn-ghost px-4 py-2 text-sm mt-5">Change password</button>
    <a href="/logout" class="btn-ghost px-4 py-2 text-sm mt-5 inline-block">Sign out everywhere</a>
  </div>
</div>

<script>
async function changePw() {
  const current = prompt('Current password:'); if (!current) return;
  const next = prompt('New password (min 8 chars):'); if (!next) return;
  try { const r = await cgptApi('/auth/change-password', { method: 'POST', body: { current_password: current, new_password: next } }); toast(r.message || 'Password changed', 'success'); setTimeout(()=>location.href='/login', 1200); }
  catch (e) { toast(e.message, 'error'); }
}
</script>

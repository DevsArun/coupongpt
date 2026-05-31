<?php
use function App\e;
/** @var array $plans */
/** @var ?array $subscription */
$plans = is_array($plans ?? null) ? $plans : [];
$sub = $subscription ?? [];
?>
<div class="mb-6"><h1 class="text-2xl font-bold">Billing</h1><p class="text-slate-400 text-sm">Manage your plan, invoices, and payments.</p></div>

<div class="card p-6 mb-6">
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <div class="text-slate-500 text-xs uppercase">Current plan</div>
      <div class="text-2xl font-extrabold mt-1"><?= e($sub['plan_name'] ?? 'Free') ?></div>
      <div class="text-sm text-slate-400 mt-1">
        <?= (int)($sub['quota_limit'] ?? 10) ?> searches / <?= e($sub['quota_window'] ?? 'day') ?> ·
        status <span class="capitalize"><?= e($sub['status'] ?? 'active') ?></span>
        <?php if (!empty($sub['current_period_end'])): ?> · renews <?= e(date('M j, Y', strtotime($sub['current_period_end']))) ?><?php endif; ?>
      </div>
    </div>
    <div class="flex gap-2">
      <a href="/pricing" class="btn-accent px-4 py-2 text-sm">Change plan</a>
      <?php if (($sub['plan'] ?? 'free') !== 'free'): ?>
        <button onclick="cancelSub()" class="btn-ghost px-4 py-2 text-sm">Cancel</button>
      <?php endif; ?>
    </div>
  </div>
</div>

<div class="grid lg:grid-cols-2 gap-4">
  <div class="card p-5"><h3 class="font-semibold mb-3">Invoices</h3><div id="invoices"></div></div>
  <div class="card p-5"><h3 class="font-semibold mb-3">Payment history</h3><div id="payments"></div></div>
</div>

<script>
async function load() {
  try {
    const inv = await cgptApi('/billing/invoices');
    renderTable('#invoices', [
      { key: 'number', label: 'Invoice' },
      { key: 'amount_cents', label: 'Amount', render: r => '$' + ((r.amount_cents||0)/100).toFixed(2) },
      { key: 'status', label: 'Status', render: r => statusPill(r.status) },
    ], inv || [], { empty: 'No invoices yet.' });
    const pay = await cgptApi('/billing/payments');
    renderTable('#payments', [
      { key: 'created_at', label: 'Date', render: r => esc((r.created_at||'').slice(0,10)) },
      { key: 'amount_cents', label: 'Amount', render: r => '$' + ((r.amount_cents||0)/100).toFixed(2) },
      { key: 'status', label: 'Status', render: r => statusPill(r.status) },
    ], pay || [], { empty: 'No payments yet.' });
  } catch (e) { toast(e.message, 'error'); }
}
async function cancelSub() {
  if (!confirm('Cancel your subscription at the end of the period?')) return;
  try { const r = await cgptApi('/billing/cancel', { method: 'POST', body: { at_period_end: true } }); toast(r.message, 'success'); }
  catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

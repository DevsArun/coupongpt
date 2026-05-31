<?php use function App\e; ?>
<div class="mb-6"><h1 class="text-2xl font-bold">Revenue &amp; Billing</h1><p class="text-slate-400 text-sm">Payments, invoices, and monthly revenue.</p></div>

<div class="card p-5 mb-6">
  <h3 class="font-semibold mb-4">Monthly revenue</h3>
  <div id="rev"></div>
</div>

<div class="grid lg:grid-cols-2 gap-4">
  <div class="card p-5"><h3 class="font-semibold mb-3">Recent payments</h3><div id="pay"></div></div>
  <div class="card p-5"><h3 class="font-semibold mb-3">Recent invoices</h3><div id="inv"></div></div>
</div>

<script>
async function load() {
  try {
    const rev = await cgptApi('/admin/analytics/revenue', { query: { months: 6 } });
    const m = rev.monthly || [];
    if (m.length) window.barchart(document.getElementById('rev'), m.map(x=>x.month), m.map(x=>x.revenue_cents/100));
    else document.getElementById('rev').innerHTML = '<div class="text-slate-600 text-sm py-8 text-center">No revenue yet.</div>';

    const pay = await cgptApi('/admin/billing/payments', { query: { page_size: 20 } });
    renderTable('#pay', [
      { key: 'id', label: 'ID' },
      { key: 'amount_cents', label: 'Amount', render: r => '$' + ((r.amount_cents||0)/100).toFixed(2) },
      { key: 'gateway', label: 'Gateway' },
      { key: 'status', label: 'Status', render: r => statusPill(r.status) },
      { key: 'actions', label: '', render: r => r.status==='succeeded' ? `<button onclick="refund(${r.id})" class="btn-ghost px-2 py-1 text-xs">Refund</button>` : '' },
    ], pay.items || [], { empty: 'No payments yet.' });

    const inv = await cgptApi('/admin/billing/invoices', { query: { page_size: 20 } });
    renderTable('#inv', [
      { key: 'number', label: 'Invoice' },
      { key: 'amount_cents', label: 'Amount', render: r => '$' + ((r.amount_cents||0)/100).toFixed(2) },
      { key: 'status', label: 'Status', render: r => statusPill(r.status) },
    ], inv.items || [], { empty: 'No invoices yet.' });
  } catch (e) { toast(e.message, 'error'); }
}
async function refund(id) {
  if (!confirm('Refund this payment?')) return;
  try { const r = await cgptApi('/billing/refund/' + id, { method: 'POST' }); toast(r.message, 'success'); load(); }
  catch (e) { toast(e.message, 'error'); }
}
document.addEventListener('DOMContentLoaded', load);
</script>

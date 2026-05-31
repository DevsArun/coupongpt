<?php
use App\Auth;
use function App\e;
/** @var array $plans */

// Fallback plan list if the backend is unavailable, mirrors the seed data.
if (empty($plans)) {
    $plans = [
        ['slug' => 'free', 'name' => 'Free', 'price_cents' => 0, 'currency' => 'USD', 'billing_period' => 'month', 'quota_limit' => 10, 'quota_window' => 'day', 'description' => 'Get started for free'],
        ['slug' => 'starter', 'name' => 'Starter', 'price_cents' => 500, 'currency' => 'USD', 'billing_period' => 'month', 'quota_limit' => 100, 'quota_window' => 'month', 'description' => 'For casual deal hunters'],
        ['slug' => 'pro', 'name' => 'Pro', 'price_cents' => 1000, 'currency' => 'USD', 'billing_period' => 'month', 'quota_limit' => 200, 'quota_window' => 'month', 'description' => 'For power users'],
        ['slug' => 'yearly_pro', 'name' => 'Yearly Pro', 'price_cents' => 4900, 'currency' => 'USD', 'billing_period' => 'year', 'quota_limit' => 100, 'quota_window' => 'day', 'description' => 'Best value, daily quota'],
        ['slug' => 'yearly_elite', 'name' => 'Yearly Elite', 'price_cents' => 9900, 'currency' => 'USD', 'billing_period' => 'year', 'quota_limit' => 200, 'quota_window' => 'day', 'description' => 'Maximum daily quota'],
    ];
}
$highlight = 'pro';
?>
<section class="max-w-7xl mx-auto px-4 pt-16 pb-6 text-center">
  <span class="badge badge-accent">SIMPLE, TRANSPARENT PRICING</span>
  <h1 class="text-4xl sm:text-5xl font-extrabold mt-4">Search smarter for <span class="text-gradient">less</span></h1>
  <p class="text-slate-400 mt-4 max-w-2xl mx-auto">Start free. Upgrade any time. Downgrade, cancel, or switch plans whenever you like.</p>
</section>

<section class="max-w-7xl mx-auto px-4 pb-20">
  <div class="grid md:grid-cols-3 xl:grid-cols-5 gap-4">
    <?php foreach ($plans as $p): $isHi = ($p['slug'] === $highlight); ?>
      <div class="card <?= $isHi ? 'ring-2 ring-accent' : '' ?> card-hover p-6 flex flex-col">
        <?php if ($isHi): ?><span class="badge badge-accent self-start mb-2">POPULAR</span><?php endif; ?>
        <h3 class="text-lg font-bold"><?= e($p['name']) ?></h3>
        <p class="text-slate-500 text-xs mt-1 min-h-[2rem]"><?= e($p['description'] ?? '') ?></p>
        <div class="mt-4">
          <span class="text-3xl font-extrabold"><?= $p['price_cents'] ? money((int)$p['price_cents'], $p['currency'] ?? 'USD') : 'Free' ?></span>
          <?php if ($p['price_cents']): ?><span class="text-slate-500 text-sm">/<?= e($p['billing_period']) ?></span><?php endif; ?>
        </div>
        <ul class="mt-5 space-y-2 text-sm text-slate-300 flex-1">
          <li>✓ <strong><?= (int)$p['quota_limit'] ?></strong> searches / <?= e($p['quota_window']) ?></li>
          <li>✓ AI query understanding</li>
          <li>✓ Verified, ranked results</li>
          <?php if (in_array($p['slug'], ['pro', 'yearly_pro', 'yearly_elite'], true)): ?>
            <li>✓ Deal alerts &amp; watchlists</li>
          <?php endif; ?>
          <?php if (str_starts_with($p['slug'], 'yearly')): ?>
            <li>✓ Priority support</li>
          <?php endif; ?>
        </ul>
        <?php if (Auth::check()): ?>
          <button onclick="cgptSubscribe('<?= e($p['slug']) ?>')" class="<?= $isHi ? 'btn-accent' : 'btn-ghost' ?> w-full mt-6 py-2.5 text-sm">
            <?= $p['price_cents'] ? 'Choose ' . e($p['name']) : 'Activate Free' ?>
          </button>
        <?php else: ?>
          <a href="/register" class="<?= $isHi ? 'btn-accent' : 'btn-ghost' ?> w-full mt-6 py-2.5 text-sm text-center block">Get started</a>
        <?php endif; ?>
      </div>
    <?php endforeach; ?>
  </div>
  <p class="text-center text-slate-500 text-sm mt-8">Lifetime &amp; custom enterprise plans available on request.</p>
</section>

<?php if (Auth::check()): ?>
<script>
  async function cgptSubscribe(slug) {
    try {
      const res = await cgptApi('/billing/checkout', { method: 'POST', body: { plan_slug: slug, gateway: 'stripe' } });
      if (res.mode === 'redirect' && res.checkout_url) { location.href = res.checkout_url; return; }
      toast(res.message || 'Subscription updated!', 'success');
      setTimeout(() => location.href = '/app/billing', 900);
    } catch (e) { toast(e.message || 'Could not start checkout', 'error'); }
  }
</script>
<?php endif; ?>

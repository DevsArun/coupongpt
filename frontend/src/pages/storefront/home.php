<?php
use function App\e;
/** @var array $merchants */
?>
<section class="max-w-7xl mx-auto px-4 pt-16 pb-12 text-center">
  <div class="inline-flex items-center gap-2 badge badge-accent mb-6">
    <span class="w-1.5 h-1.5 rounded-full bg-accent2"></span> AI-POWERED · TYPO-TOLERANT · VERIFIED
  </div>
  <h1 class="text-4xl sm:text-6xl font-extrabold tracking-tight leading-tight">
    Find the <span class="text-gradient">best coupon</span><br class="hidden sm:block"> in plain English.
  </h1>
  <p class="mt-5 text-lg text-slate-400 max-w-2xl mx-auto">
    Type how you think — "best amazon coupon today", "nike offer february", even "bst niek coupn".
    Our AI understands the merchant, timing and discount intent, then ranks verified deals.
  </p>

  <form action="/search" method="get" class="mt-8 max-w-2xl mx-auto">
    <div class="card glass p-2 flex items-center gap-2 card-hover">
      <svg class="w-5 h-5 ml-3 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/></svg>
      <input id="hero-search" name="q" autocomplete="off" placeholder="Search any store, deal or promo code…"
        class="flex-1 bg-transparent outline-none px-2 py-3 text-white placeholder:text-slate-500">
      <button class="btn-accent px-5 py-3">Search</button>
    </div>
    <div id="hero-suggest" class="mt-2 text-left"></div>
  </form>

  <div class="mt-6 flex flex-wrap justify-center gap-2 text-sm">
    <?php foreach (['best amazon coupon today', 'hostinger discount', 'nike offer february', 'best vpn deal'] as $ex): ?>
      <a href="/search?q=<?= urlencode($ex) ?>" class="btn-ghost px-3 py-1.5"><?= e($ex) ?></a>
    <?php endforeach; ?>
  </div>
</section>

<section class="max-w-7xl mx-auto px-4 py-12 grid sm:grid-cols-3 gap-4">
  <?php
  $features = [
    ['Understands typos', 'Damerau-edit-distance matching + AI correction means messy queries still find the right store.'],
    ['Ranked, not just recent', 'Six signals — trust, freshness, confidence, success rate, expiry and de-duplication — decide order.'],
    ['Sub-200ms search', 'Pre-indexed in Meilisearch. We never scrape at query time, so results are instant.'],
  ];
  foreach ($features as [$t, $d]): ?>
    <div class="card card-hover p-6">
      <div class="w-10 h-10 rounded-lg btn-accent grid place-items-center mb-4 font-bold">★</div>
      <h3 class="font-semibold text-lg"><?= e($t) ?></h3>
      <p class="text-slate-400 mt-2 text-sm"><?= e($d) ?></p>
    </div>
  <?php endforeach; ?>
</section>

<?php if (!empty($merchants)): ?>
<section class="max-w-7xl mx-auto px-4 py-12">
  <div class="flex items-end justify-between mb-6">
    <h2 class="text-2xl font-bold">Popular stores</h2>
    <a href="/merchants" class="text-accent2 text-sm hover:underline">Browse all →</a>
  </div>
  <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
    <?php foreach ($merchants as $m): ?>
      <a href="/search?q=<?= urlencode($m['name'] . ' coupon') ?>" class="card card-hover p-4 text-center">
        <div class="w-12 h-12 mx-auto rounded-xl glass grid place-items-center font-bold text-lg mb-2"><?= e(strtoupper(substr($m['name'], 0, 1))) ?></div>
        <div class="text-sm font-medium truncate"><?= e($m['name']) ?></div>
        <div class="text-xs text-slate-500"><?= (int)($m['coupon_count'] ?? 0) ?> deals</div>
      </a>
    <?php endforeach; ?>
  </div>
</section>
<?php endif; ?>

<script>
  // Live autocomplete on the hero search (public /suggest passthrough).
  (function () {
    const input = document.getElementById('hero-search');
    const box = document.getElementById('hero-suggest');
    let t = null;
    function render(items) {
      if (!items.length) { box.innerHTML = ''; return; }
      box.innerHTML = '<div class="card glass overflow-hidden">' + items.map(s =>
        `<a href="/search?q=${encodeURIComponent(s.text)}" class="block px-4 py-2.5 hover:bg-white/10 text-slate-200 text-sm flex items-center justify-between">
           <span>${s.text.replace(/</g,'&lt;')}</span>
           <span class="text-[10px] uppercase text-slate-500">${s.type}</span></a>`).join('') + '</div>';
    }
    input.addEventListener('input', function () {
      clearTimeout(t);
      const q = input.value.trim();
      if (q.length < 2) { box.innerHTML = ''; return; }
      t = setTimeout(async () => {
        try {
          const res = await fetch('/suggest?q=' + encodeURIComponent(q));
          const json = await res.json();
          render(json.suggestions || []);
        } catch (e) { box.innerHTML = ''; }
      }, 180);
    });
    document.addEventListener('click', (e) => { if (!box.contains(e.target) && e.target !== input) box.innerHTML = ''; });
  })();
</script>

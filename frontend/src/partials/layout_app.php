<?php
use App\Auth;
use function App\e;
include __DIR__ . '/head.php';
?>
<body class="bg-aurora min-h-screen flex flex-col">
<header class="sticky top-0 z-40 glass border-b border-white/10">
  <div class="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
    <a href="/" class="flex items-center gap-2 font-extrabold text-lg">
      <span class="inline-grid place-items-center w-8 h-8 rounded-lg btn-accent">C</span>
      <span><?= e($appName) ?></span>
    </a>
    <nav class="hidden md:flex items-center gap-1 text-sm">
      <a href="/search" class="nav-link text-slate-300 hover:text-white">Search</a>
      <a href="/merchants" class="nav-link text-slate-300 hover:text-white">Merchants</a>
      <a href="/pricing" class="nav-link text-slate-300 hover:text-white">Pricing</a>
    </nav>
    <div class="flex items-center gap-2">
      <button onclick="window.__cmdkOpen && window.__cmdkOpen()"
        class="btn-ghost px-3 py-1.5 text-xs hidden sm:flex items-center gap-2">
        <span>Search</span><kbd class="text-[10px] bg-white/10 px-1.5 py-0.5 rounded">⌘K</kbd>
      </button>
      <?php if (Auth::check()): ?>
        <?php if (Auth::isAdmin()): ?>
          <a href="/admin" class="btn-ghost px-3 py-1.5 text-sm">Admin</a>
        <?php endif; ?>
        <a href="/app" class="btn-ghost px-3 py-1.5 text-sm">Dashboard</a>
        <a href="/logout" class="btn-accent px-3 py-1.5 text-sm">Sign out</a>
      <?php else: ?>
        <a href="/login" class="btn-ghost px-3 py-1.5 text-sm">Sign in</a>
        <a href="/register" class="btn-accent px-3 py-1.5 text-sm">Get started</a>
      <?php endif; ?>
    </div>
  </div>
</header>

<main class="flex-1 animate-in"><?= $content ?></main>

<footer class="border-t border-white/10 mt-16">
  <div class="max-w-7xl mx-auto px-4 py-10 grid md:grid-cols-4 gap-8 text-sm text-slate-400">
    <div>
      <div class="flex items-center gap-2 font-extrabold text-white mb-3">
        <span class="inline-grid place-items-center w-7 h-7 rounded-lg btn-accent text-sm">C</span>
        <?= e($appName) ?>
      </div>
      <p>AI-powered coupon search. Verified, ranked, and always fresh.</p>
    </div>
    <div><h4 class="text-white font-semibold mb-3">Product</h4>
      <ul class="space-y-2"><li><a href="/search" class="hover:text-white">Search</a></li>
      <li><a href="/merchants" class="hover:text-white">Merchants</a></li>
      <li><a href="/pricing" class="hover:text-white">Pricing</a></li></ul></div>
    <div><h4 class="text-white font-semibold mb-3">Account</h4>
      <ul class="space-y-2"><li><a href="/login" class="hover:text-white">Sign in</a></li>
      <li><a href="/register" class="hover:text-white">Create account</a></li></ul></div>
    <div><h4 class="text-white font-semibold mb-3">Legal</h4>
      <ul class="space-y-2"><li><span>Privacy</span></li><li><span>Terms</span></li></ul></div>
  </div>
  <div class="text-center text-xs text-slate-600 pb-8">© <?= date('Y') ?> <?= e($appName) ?>. Built for deal hunters.</div>
</footer>
<?php include __DIR__ . '/flash.php'; ?>
</body>
</html>

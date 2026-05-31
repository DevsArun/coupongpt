<?php
use App\Csrf;
use function App\e;
$appName = \App\Config::appName();
$ref = $_GET['ref'] ?? '';
include __DIR__ . '/../../partials/head.php';
?>
<body class="bg-aurora min-h-screen grid lg:grid-cols-2">
  <div class="hidden lg:flex flex-col justify-between p-12">
    <a href="/" class="flex items-center gap-2 font-extrabold text-xl">
      <span class="inline-grid place-items-center w-9 h-9 rounded-lg btn-accent">C</span><?= e($appName) ?>
    </a>
    <div>
      <h1 class="text-4xl font-extrabold leading-tight">Join thousands of<br><span class="text-gradient">smart shoppers</span>.</h1>
      <ul class="text-slate-400 mt-6 space-y-3 max-w-md">
        <li>✓ 10 free AI searches every day</li>
        <li>✓ Typo-tolerant, natural-language search</li>
        <li>✓ Save coupons &amp; track your favorite stores</li>
      </ul>
    </div>
    <p class="text-slate-600 text-sm">© <?= date('Y') ?> <?= e($appName) ?></p>
  </div>

  <div class="flex items-center justify-center p-6">
    <div class="w-full max-w-md card glass p-8 animate-in">
      <a href="/" class="lg:hidden flex items-center gap-2 font-extrabold text-lg mb-6">
        <span class="inline-grid place-items-center w-8 h-8 rounded-lg btn-accent">C</span><?= e($appName) ?>
      </a>
      <h2 class="text-2xl font-bold">Create your account</h2>
      <p class="text-slate-400 text-sm mt-1">Free forever. No card required.</p>

      <form method="post" action="/register" class="mt-6 space-y-4">
        <?= Csrf::field() ?>
        <div>
          <label class="text-sm text-slate-400">Full name</label>
          <input name="full_name" type="text"
            class="mt-1 w-full card bg-black/20 px-4 py-2.5 outline-none focus:ring-2 focus:ring-accent" placeholder="Jane Doe">
        </div>
        <div>
          <label class="text-sm text-slate-400">Email</label>
          <input name="email" type="email" required
            class="mt-1 w-full card bg-black/20 px-4 py-2.5 outline-none focus:ring-2 focus:ring-accent" placeholder="you@example.com">
        </div>
        <div>
          <label class="text-sm text-slate-400">Password</label>
          <input name="password" type="password" required minlength="8"
            class="mt-1 w-full card bg-black/20 px-4 py-2.5 outline-none focus:ring-2 focus:ring-accent" placeholder="At least 8 characters">
        </div>
        <input type="hidden" name="referral_code" value="<?= e($ref) ?>">
        <button class="btn-accent w-full py-2.5 font-semibold">Create account</button>
      </form>

      <p class="text-sm text-slate-400 mt-6 text-center">
        Already have an account? <a href="/login" class="text-accent2 hover:underline">Sign in</a>
      </p>
    </div>
  </div>
  <?php include __DIR__ . '/../../partials/flash.php'; ?>
</body>
</html>

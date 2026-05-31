<?php
use App\Csrf;
use function App\e;
$appName = \App\Config::appName();
include __DIR__ . '/../../partials/head.php';
?>
<body class="bg-aurora min-h-screen grid lg:grid-cols-2">
  <!-- Brand panel -->
  <div class="hidden lg:flex flex-col justify-between p-12 relative overflow-hidden">
    <a href="/" class="flex items-center gap-2 font-extrabold text-xl">
      <span class="inline-grid place-items-center w-9 h-9 rounded-lg btn-accent">C</span><?= e($appName) ?>
    </a>
    <div>
      <h1 class="text-4xl font-extrabold leading-tight">Find the <span class="text-gradient">best coupon</span><br>in plain English.</h1>
      <p class="text-slate-400 mt-4 max-w-md">Sign in to save coupons, build watchlists, and get deal alerts the moment prices drop.</p>
    </div>
    <p class="text-slate-600 text-sm">© <?= date('Y') ?> <?= e($appName) ?></p>
  </div>

  <!-- Form panel -->
  <div class="flex items-center justify-center p-6">
    <div class="w-full max-w-md card glass p-8 animate-in">
      <a href="/" class="lg:hidden flex items-center gap-2 font-extrabold text-lg mb-6">
        <span class="inline-grid place-items-center w-8 h-8 rounded-lg btn-accent">C</span><?= e($appName) ?>
      </a>
      <h2 class="text-2xl font-bold">Welcome back</h2>
      <p class="text-slate-400 text-sm mt-1">Sign in to your account.</p>

      <form method="post" action="/login" class="mt-6 space-y-4">
        <?= Csrf::field() ?>
        <div>
          <label class="text-sm text-slate-400">Email</label>
          <input name="email" type="email" required autofocus
            class="mt-1 w-full card bg-black/20 px-4 py-2.5 outline-none focus:ring-2 focus:ring-accent" placeholder="you@example.com">
        </div>
        <div>
          <label class="text-sm text-slate-400">Password</label>
          <input name="password" type="password" required
            class="mt-1 w-full card bg-black/20 px-4 py-2.5 outline-none focus:ring-2 focus:ring-accent" placeholder="••••••••">
        </div>
        <button class="btn-accent w-full py-2.5 font-semibold">Sign in</button>
      </form>

      <p class="text-sm text-slate-400 mt-6 text-center">
        New here? <a href="/register" class="text-accent2 hover:underline">Create an account</a>
      </p>
    </div>
  </div>
  <?php include __DIR__ . '/../../partials/flash.php'; ?>
</body>
</html>

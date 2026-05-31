<?php
use App\Csrf;
use function App\e;
$appName = \App\Config::appName();
include __DIR__ . '/../../partials/head.php';
?>
<body class="bg-aurora min-h-screen grid place-items-center p-6">
  <div class="w-full max-w-md card glass p-8 animate-in">
    <a href="/" class="flex items-center gap-2 font-extrabold text-lg mb-6">
      <span class="inline-grid place-items-center w-8 h-8 rounded-lg btn-accent">C</span><?= e($appName) ?>
    </a>
    <h2 class="text-2xl font-bold">Forgot password</h2>
    <p class="text-slate-400 text-sm mt-1">Enter your email and we'll send a reset link.</p>
    <form method="post" action="/forgot-password" class="mt-6 space-y-4">
      <?= Csrf::field() ?>
      <input name="email" type="email" required placeholder="you@example.com"
        class="w-full card bg-black/20 px-4 py-2.5 outline-none focus:ring-2 focus:ring-accent">
      <button class="btn-accent w-full py-2.5 font-semibold">Send reset link</button>
    </form>
    <p class="text-sm text-slate-400 mt-6 text-center"><a href="/login" class="text-accent2 hover:underline">Back to sign in</a></p>
  </div>
  <?php include __DIR__ . '/../../partials/flash.php'; ?>
</body>
</html>

<?php
declare(strict_types=1);

/**
 * CouponGPT front controller. All requests are routed here (.htaccess).
 */

require_once __DIR__ . '/../src/bootstrap.php';

use App\Auth;
use App\BackendClient;
use App\Csrf;
use App\Proxy;
use App\Router;
use App\View;

View::share('appName', \App\Config::appName());

$router = new Router();

// --- Guards -------------------------------------------------------------
$requireAuth = static function (): void {
    if (!Auth::check()) {
        flash('error', 'Please sign in to continue.');
        redirect('/login');
    }
};
$requireAdmin = static function () use ($requireAuth): void {
    $requireAuth();
    if (!Auth::isAdmin()) {
        http_response_code(403);
        View::render('errors/403', [], 'app');
        exit;
    }
};

// --- Public storefront --------------------------------------------------
$router->get('/', static fn () => (require __DIR__ . '/../src/controllers/storefront.php')('home'));
$router->get('/search', static fn () => (require __DIR__ . '/../src/controllers/storefront.php')('search'));
$router->get('/merchants', static fn () => (require __DIR__ . '/../src/controllers/storefront.php')('merchants'));
$router->get('/pricing', static fn () => (require __DIR__ . '/../src/controllers/storefront.php')('pricing'));
$router->get('/coupon/{uuid}', static fn ($p) => (require __DIR__ . '/../src/controllers/storefront.php')('coupon', $p));

// --- Auth ---------------------------------------------------------------
$router->get('/login', static fn () => View::render('auth/login', [], 'blank'));
$router->get('/register', static fn () => View::render('auth/register', [], 'blank'));
$router->post('/login', static function (): void {
    Csrf::check();
    $res = Auth::login($_POST['email'] ?? '', $_POST['password'] ?? '');
    if ($res['ok']) {
        flash('success', 'Welcome back!');
        redirect(Auth::isAdmin() ? '/admin' : '/app');
    }
    flash('error', $res['error'] ?? 'Login failed.');
    redirect('/login');
});
$router->post('/register', static function (): void {
    Csrf::check();
    $res = Auth::register(
        $_POST['email'] ?? '',
        $_POST['password'] ?? '',
        $_POST['full_name'] ?? null,
        $_POST['referral_code'] ?? null,
    );
    if ($res['ok']) {
        flash('success', 'Account created. Welcome to ' . \App\Config::appName() . '!');
        redirect('/app');
    }
    flash('error', $res['error'] ?? 'Registration failed.');
    redirect('/register');
});
$router->get('/logout', static function (): void {
    Auth::logout();
    flash('success', 'You have been signed out.');
    redirect('/');
});

// --- Authenticated JSON proxy ------------------------------------------
$router->get('/proxy', static fn () => Proxy::handle());
$router->post('/proxy', static fn () => Proxy::handle());
$router->post('/proxy/{rest}', static fn () => Proxy::handle());

// --- Public autocomplete passthrough (no auth) -------------------------
$router->get('/suggest', static function (): void {
    header('Content-Type: application/json');
    $q = trim((string)($_GET['q'] ?? ''));
    if ($q === '') {
        echo json_encode(['suggestions' => []]);
        return;
    }
    $res = (new BackendClient())->get('/search/suggest', ['q' => $q, 'limit' => 8]);
    echo json_encode($res['body'] ?? ['suggestions' => []]);
});

// --- Public click-out redirect (tracks clicks server-side) -------------
$router->get('/out/{uuid}', static function (array $p): void {
    $uuid = $p['uuid'] ?? '';
    $res = (new BackendClient())->get('/coupons/' . urlencode($uuid));
    $dest = $res['body']['landing_url'] ?? null;
    if (!$dest) {
        flash('error', 'This deal has no destination link.');
        redirect('/search');
    }
    // Best-effort click registration (feedback/click endpoints are public).
    (new BackendClient())->request('GET', '/coupons/' . urlencode($uuid) . '/go', ['timeout' => 5]);
    redirect($dest);
});

// --- Public coupon feedback (no auth required) -------------------------
$router->post('/fb', static function (): void {
    header('Content-Type: application/json');
    Csrf::check();
    $uuid = $_POST['uuid'] ?? '';
    $worked = ($_POST['worked'] ?? '') === '1';
    $client = Auth::check() ? Auth::client() : new BackendClient();
    $res = $client->post('/coupons/' . urlencode($uuid) . '/feedback', ['worked' => $worked]);
    echo json_encode($res['body'] ?? ['message' => 'ok']);
});

// --- User dashboard -----------------------------------------------------
$userPages = [
    '' => 'dashboard', 'search' => 'search', 'saved' => 'saved', 'watchlist' => 'watchlist',
    'alerts' => 'alerts', 'history' => 'history', 'notifications' => 'notifications',
    'billing' => 'billing', 'profile' => 'profile', 'referrals' => 'referrals',
];
foreach ($userPages as $slug => $view) {
    $path = '/app' . ($slug ? "/{$slug}" : '');
    $router->get($path, static function () use ($requireAuth, $view): void {
        $requireAuth();
        (require __DIR__ . '/../src/controllers/dashboard.php')($view);
    });
}
$router->post('/app/profile', static function () use ($requireAuth): void {
    $requireAuth();
    Csrf::check();
    Auth::client()->patch('/auth/me', [
        'full_name' => $_POST['full_name'] ?? null,
        'timezone' => $_POST['timezone'] ?? null,
    ]);
    flash('success', 'Profile updated.');
    redirect('/app/profile');
});

// --- Admin mission control ---------------------------------------------
$adminPages = [
    '' => 'dashboard', 'merchants' => 'merchants', 'sources' => 'sources', 'coupons' => 'coupons',
    'validation' => 'validation', 'ai' => 'ai', 'analytics' => 'analytics', 'users' => 'users',
    'subscriptions' => 'subscriptions', 'billing' => 'billing', 'logs' => 'logs',
    'queues' => 'queues', 'crawlers' => 'crawlers', 'flags' => 'flags', 'settings' => 'settings',
];
foreach ($adminPages as $slug => $view) {
    $path = '/admin' . ($slug ? "/{$slug}" : '');
    $router->get($path, static function () use ($requireAdmin, $view): void {
        $requireAdmin();
        (require __DIR__ . '/../src/controllers/admin.php')($view);
    });
}

$router->dispatch($_SERVER['REQUEST_METHOD'], current_path());

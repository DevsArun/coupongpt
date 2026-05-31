<?php
declare(strict_types=1);

/**
 * Application bootstrap: autoloader, secure session, and shared helpers.
 * Works without `composer install` via a tiny PSR-4 autoloader for App\.
 */

spl_autoload_register(static function (string $class): void {
    $prefix = 'App\\';
    if (!str_starts_with($class, $prefix)) {
        return;
    }
    $relative = substr($class, strlen($prefix));
    $file = __DIR__ . '/' . str_replace('\\', '/', $relative) . '.php';
    if (is_file($file)) {
        require $file;
    }
});

require_once __DIR__ . '/View.php'; // also defines App\e()
require_once __DIR__ . '/helpers.php';

use App\Config;

// ---- Secure session ----
if (session_status() !== PHP_SESSION_ACTIVE) {
    session_name('cgpt_session');
    session_set_cookie_params([
        'lifetime' => 0,
        'path' => '/',
        'httponly' => true,
        'samesite' => 'Lax',
        'secure' => Config::isProduction(),
    ]);
    session_start();
}

// ---- Flash messages ----
if (!isset($_SESSION['_flash'])) {
    $_SESSION['_flash'] = [];
}

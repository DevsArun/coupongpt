<?php
declare(strict_types=1);

namespace App;

/** CSRF protection for state-changing form posts in the PHP tier. */
final class Csrf
{
    public static function token(): string
    {
        if (empty($_SESSION['csrf_token'])) {
            $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
        }
        return $_SESSION['csrf_token'];
    }

    public static function field(): string
    {
        return '<input type="hidden" name="csrf_token" value="' . htmlspecialchars(self::token(), ENT_QUOTES) . '">';
    }

    public static function verify(?string $token): bool
    {
        return !empty($token) && !empty($_SESSION['csrf_token'])
            && hash_equals($_SESSION['csrf_token'], $token);
    }

    public static function check(): void
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            if (!self::verify($_POST['csrf_token'] ?? null)) {
                http_response_code(419);
                exit('Invalid CSRF token. Please refresh and try again.');
            }
        }
    }
}

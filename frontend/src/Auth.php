<?php
declare(strict_types=1);

namespace App;

/**
 * Session-based authentication for the PHP tier.
 *
 * Backend tokens are stored server-side in the PHP session only; the browser
 * receives just the PHP session cookie (HttpOnly). On access-token expiry we
 * transparently refresh using the stored refresh token.
 */
final class Auth
{
    public static function login(string $email, string $password): array
    {
        $client = new BackendClient();
        $res = $client->post('/auth/login', ['email' => $email, 'password' => $password]);
        if ($res['ok']) {
            self::store($res['body']);
        }
        return $res;
    }

    public static function register(string $email, string $password, ?string $fullName, ?string $ref): array
    {
        $client = new BackendClient();
        $payload = ['email' => $email, 'password' => $password];
        if ($fullName) {
            $payload['full_name'] = $fullName;
        }
        if ($ref) {
            $payload['referral_code'] = $ref;
        }
        $res = $client->post('/auth/register', $payload);
        if ($res['ok']) {
            self::store($res['body']);
        }
        return $res;
    }

    private static function store(array $body): void
    {
        $_SESSION['user'] = $body['user'] ?? null;
        $_SESSION['access_token'] = $body['tokens']['access_token'] ?? null;
        $_SESSION['refresh_token'] = $body['tokens']['refresh_token'] ?? null;
        $_SESSION['token_expires_at'] = time() + (int)($body['tokens']['expires_in'] ?? 1800) - 30;
    }

    public static function logout(): void
    {
        if (!empty($_SESSION['refresh_token'])) {
            (new BackendClient())->post('/auth/logout', ['refresh_token' => $_SESSION['refresh_token']]);
        }
        $_SESSION = [];
        if (session_status() === PHP_SESSION_ACTIVE) {
            session_destroy();
        }
    }

    public static function check(): bool
    {
        return !empty($_SESSION['user']) && !empty($_SESSION['access_token']);
    }

    public static function user(): ?array
    {
        return $_SESSION['user'] ?? null;
    }

    public static function role(): string
    {
        return $_SESSION['user']['role'] ?? 'guest';
    }

    public static function isAdmin(): bool
    {
        return in_array(self::role(), ['super_admin', 'admin', 'operations', 'analyst', 'moderator', 'support'], true);
    }

    /** Returns a valid access token, refreshing if needed; null if not logged in. */
    public static function token(): ?string
    {
        if (!self::check()) {
            return null;
        }
        if (time() >= (int)($_SESSION['token_expires_at'] ?? 0)) {
            self::refresh();
        }
        return $_SESSION['access_token'] ?? null;
    }

    private static function refresh(): void
    {
        if (empty($_SESSION['refresh_token'])) {
            return;
        }
        $res = (new BackendClient())->post('/auth/refresh', ['refresh_token' => $_SESSION['refresh_token']]);
        if ($res['ok']) {
            $_SESSION['access_token'] = $res['body']['access_token'] ?? $_SESSION['access_token'];
            $_SESSION['refresh_token'] = $res['body']['refresh_token'] ?? $_SESSION['refresh_token'];
            $_SESSION['token_expires_at'] = time() + (int)($res['body']['expires_in'] ?? 1800) - 30;
        } else {
            // refresh failed -> force logout
            $_SESSION = [];
        }
    }

    /** Authenticated backend client bound to the current user's token. */
    public static function client(): BackendClient
    {
        return new BackendClient(self::token());
    }
}

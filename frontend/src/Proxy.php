<?php
declare(strict_types=1);

namespace App;

/**
 * Authenticated backend-for-frontend proxy.
 *
 * The browser cannot call the FastAPI backend directly (tokens are kept
 * server-side). This proxy forwards a constrained set of API paths, attaching
 * the session's access token. Writes require a valid CSRF token. A path
 * allow-list prevents this from becoming an open proxy / SSRF vector.
 */
final class Proxy
{
    /** Path prefixes any authenticated user may reach. */
    private const USER_PREFIXES = [
        '/search', '/coupons', '/merchants', '/auth/me', '/me/', '/billing/plans',
    ];

    /** Path prefixes that additionally require an admin-class role. */
    private const ADMIN_PREFIXES = ['/admin'];

    public static function handle(): void
    {
        header('Content-Type: application/json');

        if (!Auth::check()) {
            http_response_code(401);
            echo json_encode(['error' => 'Not authenticated']);
            return;
        }

        $method = $_SERVER['REQUEST_METHOD'];
        $isWrite = in_array($method, ['POST', 'PUT', 'PATCH', 'DELETE'], true);

        $payload = [];
        if ($isWrite) {
            $payload = json_decode(file_get_contents('php://input') ?: '[]', true) ?: [];
            if (!Csrf::verify($payload['csrf_token'] ?? ($_SERVER['HTTP_X_CSRF_TOKEN'] ?? null))) {
                http_response_code(419);
                echo json_encode(['error' => 'Invalid CSRF token']);
                return;
            }
            unset($payload['csrf_token']);
        }

        $path = $_GET['path'] ?? '';
        if (!is_string($path) || $path === '' || $path[0] !== '/') {
            http_response_code(400);
            echo json_encode(['error' => 'Invalid path']);
            return;
        }

        if (!self::allowed($path)) {
            http_response_code(403);
            echo json_encode(['error' => 'Path not allowed']);
            return;
        }

        $query = $_GET;
        unset($query['path'], $query['route']);

        $client = Auth::client();
        $opts = ['token' => Auth::token(), 'query' => $query];
        if ($isWrite) {
            $opts['json'] = $payload;
        }
        $res = $client->request($method, $path, $opts);

        http_response_code($res['status'] ?: 502);
        echo json_encode($res['body']);
    }

    private static function allowed(string $path): bool
    {
        foreach (self::ADMIN_PREFIXES as $p) {
            if (str_starts_with($path, $p)) {
                return Auth::isAdmin();
            }
        }
        foreach (self::USER_PREFIXES as $p) {
            if (str_starts_with($path, $p)) {
                return true;
            }
        }
        return false;
    }
}

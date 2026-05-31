<?php
declare(strict_types=1);

namespace App;

/**
 * Thin HTTP proxy to the FastAPI backend.
 *
 * This is the ONLY way the PHP tier talks to data — it never touches MySQL,
 * Redis, or Meilisearch directly. The user's access token is attached
 * server-side (from the PHP session), so the browser never sees raw tokens.
 */
final class BackendClient
{
    private string $base;

    public function __construct(?string $accessToken = null)
    {
        $this->base = Config::backendBaseUrl() . Config::apiPrefix();
        $this->accessToken = $accessToken;
    }

    private ?string $accessToken;

    /** @return array{status:int, body:array, ok:bool, error:?string} */
    public function request(string $method, string $path, array $options = []): array
    {
        $url = $this->base . $path;
        if (!empty($options['query'])) {
            $url .= '?' . http_build_query($options['query']);
        }

        $headers = ['Accept: application/json'];
        if (isset($options['json'])) {
            $headers[] = 'Content-Type: application/json';
        }
        $token = $options['token'] ?? $this->accessToken;
        if ($token) {
            $headers[] = 'Authorization: Bearer ' . $token;
        }
        // Forward the real browser IP so the backend (with TRUST_PROXY_HEADERS=true)
        // applies rate limits / anonymous quotas per end-user, not per frontend host.
        if (function_exists('client_ip')) {
            $ip = client_ip();
            if ($ip) {
                $headers[] = 'X-Forwarded-For: ' . $ip;
                $headers[] = 'X-Real-IP: ' . $ip;
            }
        }
        foreach ($options['headers'] ?? [] as $h) {
            $headers[] = $h;
        }

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_CUSTOMREQUEST => strtoupper($method),
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => $headers,
            CURLOPT_TIMEOUT => (int)($options['timeout'] ?? 20),
            CURLOPT_CONNECTTIMEOUT => 5,
        ]);
        if (isset($options['json'])) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($options['json']));
        } elseif (isset($options['form'])) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($options['form']));
        }

        $raw = curl_exec($ch);
        $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlErr = curl_error($ch);
        curl_close($ch);

        if ($raw === false) {
            return ['status' => 0, 'body' => [], 'ok' => false, 'error' => $curlErr ?: 'connection_failed'];
        }

        $body = json_decode($raw, true);
        if (!is_array($body)) {
            $body = ['raw' => $raw];
        }
        $ok = $status >= 200 && $status < 300;
        $error = null;
        if (!$ok) {
            $error = $body['error']['message'] ?? ($body['detail'] ?? 'Request failed');
            if (is_array($error)) {
                $error = 'Request failed';
            }
        }
        return ['status' => $status, 'body' => $body, 'ok' => $ok, 'error' => $error];
    }

    public function get(string $path, array $query = [], ?string $token = null): array
    {
        return $this->request('GET', $path, ['query' => $query, 'token' => $token]);
    }

    public function post(string $path, array $json = [], ?string $token = null): array
    {
        return $this->request('POST', $path, ['json' => $json, 'token' => $token]);
    }

    public function patch(string $path, array $json = [], ?string $token = null): array
    {
        return $this->request('PATCH', $path, ['json' => $json, 'token' => $token]);
    }

    public function put(string $path, array $json = [], ?string $token = null): array
    {
        return $this->request('PUT', $path, ['json' => $json, 'token' => $token]);
    }
}

<?php
declare(strict_types=1);

use App\Auth;
use App\BackendClient;
use App\View;

/**
 * Storefront controller. Returns a callable($view, $params) that renders
 * public pages, fetching data from the backend as needed.
 */
return static function (string $view, array $params = []): void {
    $client = Auth::check() ? Auth::client() : new BackendClient();

    switch ($view) {
        case 'home':
            $merchants = $client->get('/merchants', ['page_size' => 12]);
            View::render('storefront/home', [
                'merchants' => $merchants['body']['items'] ?? [],
            ], 'app');
            return;

        case 'search':
            $q = trim((string)($_GET['q'] ?? ''));
            $result = null;
            if ($q !== '') {
                $result = $client->get('/search', ['q' => $q, 'limit' => 24]);
            }
            View::render('storefront/search', [
                'q' => $q,
                'result' => $result['body'] ?? null,
                'ok' => $result['ok'] ?? false,
                'error' => $result['error'] ?? null,
            ], 'app');
            return;

        case 'merchants':
            $q = trim((string)($_GET['q'] ?? ''));
            $merchants = $client->get('/merchants', array_filter(['q' => $q ?: null, 'page_size' => 48]));
            View::render('storefront/merchants', [
                'q' => $q,
                'merchants' => $merchants['body']['items'] ?? [],
            ], 'app');
            return;

        case 'pricing':
            $plans = $client->get('/billing/plans');
            View::render('storefront/pricing', [
                'plans' => $plans['body'] ?? [],
            ], 'app');
            return;

        case 'coupon':
            $res = $client->get('/coupons/' . urlencode($params['uuid'] ?? ''));
            if (!($res['ok'] ?? false)) {
                http_response_code(404);
                View::render('errors/404', [], 'app');
                return;
            }
            View::render('storefront/coupon', ['coupon' => $res['body']], 'app');
            return;

        default:
            http_response_code(404);
            View::render('errors/404', [], 'app');
    }
};

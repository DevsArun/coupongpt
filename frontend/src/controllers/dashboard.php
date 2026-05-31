<?php
declare(strict_types=1);

use App\Auth;
use App\View;

/** User dashboard controller. Returns callable($view). */
return static function (string $view): void {
    $client = Auth::client();
    $data = ['active' => $view];

    switch ($view) {
        case 'dashboard':
            $quota = $client->get('/search/quota');
            $data['quota'] = $quota['body'] ?? null;
            break;

        case 'billing':
            $plans = $client->get('/billing/plans');
            $sub = $client->get('/me/subscription');
            $data['plans'] = $plans['body']['items'] ?? ($plans['body'] ?? []);
            $data['subscription'] = $sub['body'] ?? null;
            break;

        case 'profile':
            $me = $client->get('/auth/me');
            $data['me'] = $me['body'] ?? Auth::user();
            break;
    }

    View::render('dashboard/' . $view, $data, 'dashboard');
};

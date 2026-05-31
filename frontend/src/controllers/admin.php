<?php
declare(strict_types=1);

use App\Auth;
use App\View;

/** Admin mission-control controller. Returns callable($view). */
return static function (string $view): void {
    $client = Auth::client();
    $data = ['active' => $view];

    // Server-side render the dashboard summary; other pages hydrate via /proxy.
    if ($view === 'dashboard') {
        $res = $client->get('/admin/dashboard');
        $data['dashboard'] = $res['body'] ?? null;
        $data['error'] = $res['ok'] ? null : ($res['error'] ?? 'Failed to load dashboard');
    }

    View::render('admin/' . $view, $data, 'admin');
};

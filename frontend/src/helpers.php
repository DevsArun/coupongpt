<?php
declare(strict_types=1);

use App\Config;

/** Flash a one-time message: success|error|info. */
function flash(string $type, string $message): void
{
    $_SESSION['_flash'][] = ['type' => $type, 'message' => $message];
}

/** Pull and clear all flash messages. */
function take_flashes(): array
{
    $f = $_SESSION['_flash'] ?? [];
    $_SESSION['_flash'] = [];
    return $f;
}

/** Redirect helper. */
function redirect(string $path): never
{
    header('Location: ' . $path);
    exit;
}

/** Current request path (without query string). */
function current_path(): string
{
    $uri = $_SERVER['REQUEST_URI'] ?? '/';
    return parse_url($uri, PHP_URL_PATH) ?: '/';
}

/** Build a URL relative to the frontend root. */
function url(string $path = '/'): string
{
    return $path;
}

/** Best-effort real client IP (honours an upstream proxy's X-Forwarded-For). */
function client_ip(): ?string
{
    $xff = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? '';
    if ($xff !== '') {
        $first = trim(explode(',', $xff)[0]);
        if ($first !== '') {
            return $first;
        }
    }
    return $_SERVER['REMOTE_ADDR'] ?? null;
}

/** Format cents into a currency string. */
function money(int $cents, string $currency = 'USD'): string
{
    $symbols = ['USD' => '$', 'INR' => '₹', 'EUR' => '€', 'GBP' => '£'];
    $sym = $symbols[$currency] ?? '';
    return $sym . number_format($cents / 100, 2);
}

/** Human-friendly relative time from an ISO timestamp. */
function time_ago(?string $iso): string
{
    if (!$iso) {
        return '—';
    }
    $ts = strtotime($iso);
    if ($ts === false) {
        return '—';
    }
    $diff = time() - $ts;
    if ($diff < 60) {
        return 'just now';
    }
    foreach ([[31536000, 'year'], [2592000, 'month'], [86400, 'day'], [3600, 'hour'], [60, 'minute']] as [$secs, $label]) {
        if ($diff >= $secs) {
            $n = (int) floor($diff / $secs);
            return $n . ' ' . $label . ($n > 1 ? 's' : '') . ' ago';
        }
    }
    return 'just now';
}

/** Render a discount badge label from a coupon array. */
function discount_label(array $coupon): string
{
    $type = $coupon['discount_type'] ?? 'other';
    $val = $coupon['discount_value'] ?? null;
    return match ($type) {
        'percentage' => $val ? ((int) $val) . '% OFF' : 'DISCOUNT',
        'fixed' => $val ? money((int) ($val * 100), $coupon['currency'] ?? 'USD') . ' OFF' : 'DISCOUNT',
        'free_shipping' => 'FREE SHIPPING',
        'bogo' => 'BOGO',
        'trial' => 'FREE TRIAL',
        default => 'DEAL',
    };
}

/** Active-nav helper for sidebars. */
function nav_active(string $path, string $current): string
{
    return str_starts_with($current, $path)
        ? 'bg-white/10 text-white'
        : 'text-slate-400 hover:text-white hover:bg-white/5';
}

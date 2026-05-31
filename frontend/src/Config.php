<?php
declare(strict_types=1);

namespace App;

/**
 * Reads configuration from environment variables so the same image runs in
 * local Docker, a VPS, or anywhere else without code changes.
 */
final class Config
{
    public static function get(string $key, ?string $default = null): ?string
    {
        $value = getenv($key);
        if ($value === false || $value === '') {
            return $default;
        }
        return $value;
    }

    public static function backendBaseUrl(): string
    {
        return rtrim(self::get('BACKEND_BASE_URL', 'http://backend:8000') ?? '', '/');
    }

    public static function apiPrefix(): string
    {
        return self::get('API_V1_PREFIX', '/api/v1') ?? '/api/v1';
    }

    public static function appName(): string
    {
        return self::get('APP_NAME', 'CouponGPT') ?? 'CouponGPT';
    }

    public static function frontendBaseUrl(): string
    {
        return rtrim(self::get('FRONTEND_BASE_URL', 'http://localhost:8080') ?? '', '/');
    }

    public static function sessionSecret(): string
    {
        return self::get('SESSION_SECRET', 'change-me-session-secret') ?? 'change-me';
    }

    public static function isProduction(): bool
    {
        return (self::get('APP_ENV', 'development') ?? '') === 'production';
    }

    public static function stripePublishableKey(): string
    {
        return self::get('STRIPE_PUBLISHABLE_KEY', '') ?? '';
    }

    public static function razorpayKeyId(): string
    {
        return self::get('RAZORPAY_KEY_ID', '') ?? '';
    }
}

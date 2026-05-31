<?php
declare(strict_types=1);

namespace App;

/** Minimal view renderer with layout support and HTML escaping helpers. */
final class View
{
    private static array $shared = [];

    public static function share(string $key, mixed $value): void
    {
        self::$shared[$key] = $value;
    }

    /**
     * Render a page template inside a layout.
     *
     * @param string $page   path under src/pages (without .php)
     * @param array  $data   variables exposed to the template
     * @param string $layout one of: app, dashboard, admin, blank
     */
    public static function render(string $page, array $data = [], string $layout = 'app'): void
    {
        $data = array_merge(self::$shared, $data);
        $pageFile = __DIR__ . '/pages/' . $page . '.php';
        if (!is_file($pageFile)) {
            http_response_code(500);
            echo "View not found: {$page}";
            return;
        }

        // Capture the page content.
        extract($data, EXTR_SKIP);
        ob_start();
        include $pageFile;
        $content = ob_get_clean();

        if ($layout === 'blank') {
            echo $content;
            return;
        }

        $layoutFile = __DIR__ . '/partials/layout_' . $layout . '.php';
        if (!is_file($layoutFile)) {
            echo $content;
            return;
        }
        include $layoutFile;
    }
}

/** Escape helper used throughout templates. */
function e(?string $value): string
{
    return htmlspecialchars($value ?? '', ENT_QUOTES, 'UTF-8');
}

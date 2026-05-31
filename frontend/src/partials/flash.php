<?php
use function App\e;
$flashes = take_flashes();
if ($flashes):
?>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    <?php foreach ($flashes as $f): ?>
    window.toast(<?= json_encode($f['message']) ?>, <?= json_encode($f['type']) ?>);
    <?php endforeach; ?>
  });
</script>
<?php endif; ?>

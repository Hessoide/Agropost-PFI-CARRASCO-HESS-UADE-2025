<script>
  import { getConfig } from "../lib/config";
  const cfg = getConfig();
  const mapHref       = "#/map";           // usa centro por defecto de Config
  const mapHrefMock   = "#/map?mock=1";    // arranca simulación
</script>

<main class="home">
  <section class="panel">
    <h1>AgroPost</h1>
    <nav class="menu">
      <a class="btn" href={mapHref}>Mapa</a>
      <a class="btn" href={mapHrefMock}>Mapa (simulación)</a>
      <a class="btn" href="#/registros">Registros</a>
      <a class="btn" href="#/config">Configuración</a>
    </nav>
    <p class="hint">Centro por defecto: {cfg.defaultLat}, {cfg.defaultLon} (zoom {cfg.defaultZoom}). Cambialo en Configuración.</p>
  </section>
</main>

<style>
  .home{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
  .panel{ display:grid; gap:12px; width:100%; max-width:520px; }
  .menu{ display:flex; gap:12px; flex-wrap:wrap; }
  .btn{ padding:.6rem .9rem; border:1px solid #ccc; border-radius:.5rem; background:#fff; color:#111; text-decoration:none; }
  .btn:focus{ outline:2px solid #333; outline-offset:2px; }
  .hint{ opacity:.7; }
</style>
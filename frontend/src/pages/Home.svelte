<script>
  import { getConfig } from "../lib/config";
  const cfg = getConfig();
  const mapHref       = "#/map";           // usa centro por defecto de Config
</script>

<main class="home">
  <section class="panel">
    <h1>AgroPost</h1>
    <nav class="menu">
      <a class="btn" href="#/campo">Campo (GeoJSON)</a>
      <a class="btn" href="#/campo">cargar campo nuevo</a>
      <a class="btn" href="#/campos">seleccionar campo</a>
      <a class="btn" href="#/config">configuracion</a>
    </nav>
    <p class="hint">Centro por defecto: {cfg.defaultLat}, {cfg.defaultLon} (zoom {cfg.defaultZoom}). Cambialo en Configuración.</p>
  </section>
</main>

<style>
  .home{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
  .panel{ display:grid; gap:12px; width:100%; max-width:520px; }
  .menu{ display:flex; gap:12px; flex-wrap:wrap; }
  .hint{ opacity:.7; }
</style>

<script>
  import { getConfig } from "../lib/config";
  const cfg = getConfig();
  const mapHref       = "#/map";           // usa centro por defecto de Config

  function handleNuevoCampo() {
    const nombre = window.prompt("Nombre del campo nuevo:");
    if (nombre === null) return;
    const trimmed = nombre.trim();
    if (!trimmed) return;
    const qs = new URLSearchParams();
    qs.set("nuevo", "1");
    qs.set("nombre", trimmed);
    location.hash = `#/campo?${qs.toString()}`;
  }
</script>

<main class="home">
  <section class="panel">
    <h1>AgroPost</h1>
    <nav class="menu">
      <a class="btn" href="#/campo">Campo (GeoJSON)</a>
      <button class="btn" type="button" on:click={handleNuevoCampo}>cargar campo nuevo</button>
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
  .btn{ font: inherit; }
</style>

<script>
  import BackButton from "../components/BackButton.svelte";
  import { getConfig, saveConfig, defaults } from "../lib/config";

  let cfg = getConfig();
  let savedMsg = "";

  function save() {
    // saneo básico
    cfg.defaultZoom = Math.min(28, Math.max(1, Number(cfg.defaultZoom || defaults.defaultZoom)));
    cfg.defaultLat  = Math.min(90,  Math.max(-90, Number(cfg.defaultLat  || defaults.defaultLat)));
    cfg.defaultLon  = Math.min(180, Math.max(-180,Number(cfg.defaultLon || defaults.defaultLon)));
    saveConfig(cfg);
    savedMsg = "Guardado ✔";
    setTimeout(() => (savedMsg = ""), 1500);
  }
</script>

<div class="ui"><BackButton /></div>

<main class="wrap">
  <section class="panel">
    <h2>Configuración</h2>

    <label>WebSocket URL
      <input type="text" placeholder="ws://localhost:8000/ws" bind:value={cfg.wsUrl} />
    </label>

    <div class="grid">
      <label>Lat por defecto <input type="number" step="0.000001" bind:value={cfg.defaultLat} /></label>
      <label>Lon por defecto <input type="number" step="0.000001" bind:value={cfg.defaultLon} /></label>
      <label>Zoom por defecto <input type="number" step="0.5" bind:value={cfg.defaultZoom} /></label>
    </div>

    <label class="row"><input type="checkbox" bind:checked={cfg.offline} /> Modo offline (sin mapa base)</label>
    <label class="row"><input type="checkbox" bind:checked={cfg.showGrid} /> Mostrar cuadrícula</label>

    <button class="btn" on:click={save}>Guardar</button>
    <span class="ok">{savedMsg}</span>
  </section>
</main>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  .wrap{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
  .panel{ width:100%; max-width:560px; display:grid; gap:12px; }
  .grid{ display:grid; grid-template-columns: 1fr 1fr 1fr; gap:8px; }
  label{ display:flex; align-items:center; gap:8px; }
  input[type="text"], input[type="number"]{ flex:1; }
  .row{ gap:10px; }
  .btn{ padding:.6rem .9rem; border:1px solid #ccc; border-radius:.5rem; background:#fff; color:#111; cursor:pointer; }
  .ok{ margin-left:8px; color:green; }
</style>
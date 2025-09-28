<script>
  import { onMount } from "svelte";
  import BackButton from "../components/BackButton.svelte";
  import Mapa from "../Mapa.svelte";

  let initLat = null, initLon = null, initZoom = 18, useMock = false;
  let geoUrl = null;
  let campoId = null;

  function readParams() {
    const qs = new URLSearchParams((location.hash.split("?")[1] || ""));
    const lat = parseFloat(qs.get("lat"));
    const lon = parseFloat(qs.get("lon"));
    initLat  = Number.isFinite(lat) ? lat : null;
    initLon  = Number.isFinite(lon) ? lon : null;
    initZoom = qs.get("z") ? parseFloat(qs.get("z")) : 18;
    useMock  = qs.get("mock") === "1";
    const geo = qs.get("geo");
    const campo = qs.get("campo");
    geoUrl = (geo && geo.startsWith('/')) ? geo : null;
    campoId = campo || null;
  }

  onMount(() => {
    readParams();
    window.addEventListener("hashchange", readParams);
    return () => window.removeEventListener("hashchange", readParams);
  });

  // Fuerza remontar <Mapa/> cuando cambian parámetros o el hash
  $: componentKey = JSON.stringify({ initLat, initLon, initZoom, useMock, geoUrl, campoId });
</script>

<div class="ui"><BackButton /></div>

<div class="page">
  {#key componentKey}
    <!-- Modo minimal solo cuando NO es simulación -->
    <Mapa {initLat} {initLon} {initZoom} {useMock} {geoUrl} {campoId} minimal={false} />
  {/key}
</div>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  /* Forzar pantalla completa del mapa y evitar max-width del contenedor */
  :global(#app){ max-width: none; margin: 0; padding: 0; width:100vw; }
  .page{ position:fixed; inset:0; }
</style>

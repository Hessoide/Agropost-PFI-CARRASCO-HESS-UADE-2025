<script>
  import { onMount } from "svelte";
  import BackButton from "../components/BackButton.svelte";
  import Mapa from "../Mapa.svelte";

  let initLat = null, initLon = null, initZoom = 18, useMock = false;
  let geoUrl = null;
  let campoId = null;
  let mapaRef;
  let isSaving = false;

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

  async function handleBeforeNavigate(event) {
    if (isSaving) {
      event.detail.cancel = true;
      return;
    }
    if (!mapaRef || typeof mapaRef.getCurrentSnapshot !== 'function' || !campoId) {
      return;
    }
    const snapshot = mapaRef.getCurrentSnapshot();
    const hasData = snapshot && ((snapshot.coverage && snapshot.coverage.geometry) || (snapshot.line && snapshot.line.geometry) || (Array.isArray(snapshot.rawLine) && snapshot.rawLine.length > 1));
    if (!hasData) {
      return;
    }

    event.detail.cancel = true;
    isSaving = true;
    try {
      await saveCurrentTrack(snapshot);
      event.detail.navigate();
    } catch (err) {
      console.error('[map] guardar recorrido', err);
      alert(`No se pudo guardar el recorrido: ${err.message || err}`);
    } finally {
      isSaving = false;
    }
  }

  async function saveCurrentTrack(snapshot) {
    if (!campoId || !geoUrl) return;
    let filename = decodeURIComponent(geoUrl.split('/').pop() || '');
    if (!filename.endsWith('.geojson')) return;

    const apiUrl = `/api/campos/${encodeURIComponent(campoId)}/recorridos/${encodeURIComponent(filename)}`;

    const cloneFeatureWithRole = (feat, role) => {
      if (!feat || typeof feat !== 'object' || feat.type !== 'Feature') return null;
      const copy = JSON.parse(JSON.stringify(feat));
      if (!copy.properties || typeof copy.properties !== 'object') copy.properties = {};
      copy.properties.role = role;
      return copy;
    };

    const lineFeature = cloneFeatureWithRole(snapshot.line, 'line');
    const coverageFeature = cloneFeatureWithRole(snapshot.coverage, 'coverage');

    const payload = {
      line: lineFeature,
      coverage: coverageFeature,
      meta: {
        savedAt: new Date().toISOString(),
        areaHa: Number.isFinite(snapshot.areaHa) ? snapshot.areaHa : null,
        maquinaria: snapshot.maquinaria || null,
        maquinariaAncho: snapshot.maquinariaAncho || null,
        rawPointCount: Array.isArray(snapshot.rawLine) ? snapshot.rawLine.length : 0
      }
    };

    if (Array.isArray(snapshot.rawLine) && snapshot.rawLine.length) {
      payload.meta.rawLine = snapshot.rawLine;
    }

    const res = await fetch(apiUrl, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const msg = await res.text().catch(() => res.statusText);
      throw new Error(msg || `HTTP ${res.status}`);
    }
  }


  $: componentKey = JSON.stringify({ initLat, initLon, initZoom, useMock, geoUrl, campoId });
</script>


<div class="ui"><BackButton on:beforeNavigate={handleBeforeNavigate} /></div>

<div class="page">
  {#key componentKey}
    <!-- Modo minimal solo cuando NO es simulaci9n -->
    <Mapa bind:this={mapaRef} {initLat} {initLon} {initZoom} {useMock} {geoUrl} {campoId} minimal={false} noTiles={true} showScale={true} showGrid={true} />
  {/key}
</div>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  /* Forzar pantalla completa del mapa y evitar max-width del contenedor */
  :global(#app){ max-width: none; margin: 0; padding: 0; width:100vw; }
  .page{ position:fixed; inset:0; }
</style>

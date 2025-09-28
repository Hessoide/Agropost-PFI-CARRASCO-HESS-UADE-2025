<script>
  import BackButton from "../components/BackButton.svelte";
  import Mapa from "../Mapa.svelte";
  import { onMount } from "svelte";

  const DEFAULT_GEO = "/geo/campo1.geojson";

  let geoUrl = DEFAULT_GEO;
  let isNuevo = false;
  let campoNombre = "";
  let guardando = false;
  let saveError = null;
  let campoGuardado = false;

  function updateFromHash() {
    const qs = new URLSearchParams((location.hash.split("?")[1] || ""));
    isNuevo = qs.get("nuevo") === "1";
    const nombreParam = qs.get("nombre");
    campoNombre = nombreParam ? nombreParam.trim() : "";
    const geoParam = qs.get("geo");
    geoUrl = geoParam && geoParam.startsWith('/') ? geoParam : DEFAULT_GEO;
    if (isNuevo) {
      geoUrl = null;
    }
  }

  updateFromHash();

  onMount(() => {
    window.addEventListener("hashchange", updateFromHash);
    return () => window.removeEventListener("hashchange", updateFromHash);
  });

  async function parseErrorResponse(res) {
    try {
      const data = await res.json();
      if (data && typeof data.detail === "string") return data.detail;
      if (data && typeof data.error === "string") return data.error;
    } catch (err) {
      // ignore
    }
    return `HTTP ${res.status}`;
  }

  async function guardarCampo() {
    if (!campoNombre) {
      saveError = "Falta el nombre del campo.";
      return;
    }
    guardando = true;
    saveError = null;
    campoGuardado = false;
    try {
      const res = await fetch("/api/campos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: campoNombre })
      });
      if (!res.ok) {
        throw new Error(await parseErrorResponse(res));
      }
      const data = await res.json();
      campoGuardado = true;
      const nextId = data?.campo?.id;
      if (nextId) {
        location.hash = `#/campo-menu?id=${encodeURIComponent(nextId)}`;
      }
    } catch (e) {
      saveError = e instanceof Error ? e.message : String(e);
    } finally {
      guardando = false;
    }
  }
</script>

<div class="ui">
  <BackButton />
  {#if isNuevo}
    <button
      class="btn guardar"
      type="button"
      on:click={guardarCampo}
      disabled={guardando || campoGuardado || !campoNombre}
    >
      {#if guardando}
        guardando...
      {:else if campoGuardado}
        guardado
      {:else}
        guardar
      {/if}
    </button>
    {#if saveError}
      <p class="err">{saveError}</p>
    {/if}
  {/if}
</div>

<div class="page">
  <Mapa minimal={false} noTiles={true} {geoUrl} showScale={true} showGrid={true} />
</div>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; display:flex; flex-direction:column; gap:8px; }
  .btn{ padding:10px 14px; border:1px solid #aaa; border-radius:6px; background:#fff; color:#111; cursor:pointer; font: inherit; }
  .btn:disabled{ opacity:.6; cursor:not-allowed; }
  .btn.guardar{ border-color:#2e7d32; color:#1b5e20; }
  .btn.guardar:not(:disabled){ background:#e8f5e9; }
  .err{ margin:0; color:crimson; max-width:220px; }
  :global(#app){ max-width: none; margin: 0; padding: 0; width:100vw; }
  .page{ position:fixed; inset:0; }
</style>

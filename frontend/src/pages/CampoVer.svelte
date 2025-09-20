<script>
  import BackButton from "../components/BackButton.svelte";
  import Mapa from "../Mapa.svelte";
  import { onMount } from "svelte";

  let id = null;
  let geoUrl = null;

  function updateFromHash() {
    const qs = new URLSearchParams((location.hash.split("?")[1] || ""));
    id = qs.get("id");
    geoUrl = id ? `/campos%20guardados/${encodeURIComponent(id)}/area.geojson` : null;
  }

  onMount(() => {
    updateFromHash();
    window.addEventListener("hashchange", updateFromHash);
    return () => window.removeEventListener("hashchange", updateFromHash);
  });
</script>

<div class="ui"><BackButton /></div>

<div class="page">
  {#if geoUrl}
    <Mapa minimal={false} noTiles={true} {geoUrl} showScale={true} showGrid={true} />
  {:else}
    <div class="empty">Falta el parámetro id del campo.</div>
  {/if}
</div>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  :global(#app){ max-width: none; margin: 0; padding: 0; width:100vw; }
  .page{ position:fixed; inset:0; }
  .empty{ display:flex; align-items:center; justify-content:center; height:100vh; }
</style>


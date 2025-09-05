<script>
  import BackButton from "../components/BackButton.svelte";
  import Mapa from "../Mapa.svelte";

  // Página que muestra sólo el contenido del GeoJSON 'campo1' sin tiles
  const geoUrl = "/geo/campo1.geojson";
</script>

<div class="ui"><BackButton /></div>

<div class="page">
  <Mapa minimal={false} noTiles={true} {geoUrl} showScale={true} showGrid={true} />
  <!-- minimal=true oculta HUD/WS; noTiles=true evita cargar capa base -->
</div>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  :global(#app){ max-width: none; margin: 0; padding: 0; width:100vw; }
  .page{ position:fixed; inset:0; }
</style>

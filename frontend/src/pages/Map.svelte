<script>
  import BackButton from "../components/BackButton.svelte";
  import Mapa from "../Mapa.svelte"; // usa tu componente existente del mapa
</script>

<!-- UI flotante arriba a la izquierda -->
<div class="ui">
  <a href="#/" class="btn">Inicio</a>
</div>

<Mapa />

<style>
  .ui {
    position: fixed;
    top: 12px;
    left: 12px;
    display: flex;
    gap: 8px;
    z-index: 2000; /* > que los controles de Leaflet (1000–1003) */
  }
</style>
<!-- frontend/src/components/BackButton.svelte -->
<script>
  export let label = "← Atrás";
  function goBack() {
    if (history.length > 1) history.back();
    else location.hash = "#/"; // fallback a Home si no hay historial
  }
</script>

<button class="btn" type="button" on:click={goBack} aria-label="Volver">
  {label}
</button>
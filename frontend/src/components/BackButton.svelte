<script>
  export let label = "← Atrás";
  export let fallback = "#/";
  export let forceFallback = false;

  function goBack() {
    if (forceFallback) {
      location.hash = fallback;
      return;
    }
    if (history.length > 1) history.back();
    else location.hash = fallback;
  }
</script>

<button class="btn" type="button" on:click={goBack} aria-label="Volver">
  {label}
</button>

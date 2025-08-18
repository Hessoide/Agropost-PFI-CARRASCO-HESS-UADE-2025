<script>
  export let label = "← Atrás";
  function goBack() {
    if (history.length > 1) history.back();
    else location.hash = "#/";
  }
</script>

<button class="btn" type="button" on:click={goBack}>{label}</button>
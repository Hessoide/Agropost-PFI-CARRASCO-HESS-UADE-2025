<script>
  import { createEventDispatcher } from "svelte";

  export let label = "← Atrás";
  export let fallback = "#/";
  export let forceFallback = false;

  const dispatch = createEventDispatcher();

  function navigateDefault() {
    if (forceFallback) {
      location.hash = fallback;
    } else if (history.length > 1) {
      history.back();
    } else {
      location.hash = fallback;
    }
  }

  function goBack() {
    const detail = { cancel: false, navigate: navigateDefault };
    dispatch('beforeNavigate', detail);
    if (detail.cancel) return;
    detail.navigate();
  }
</script>

<button class="btn" type="button" on:click={goBack} aria-label="Volver">
  {label}
</button>

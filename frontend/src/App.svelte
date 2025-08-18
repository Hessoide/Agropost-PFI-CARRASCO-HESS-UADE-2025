<script>
  import { onMount } from "svelte";
  import Home from "./pages/Home.svelte";
  import MapPage from "./pages/Map.svelte";
  import Config from "./pages/Config.svelte";
  import Registros from "./pages/Registros.svelte";
  import NotFound from "./pages/NotFound.svelte";

  // Mapea rutas -> componente
  const routes = {
    "/": Home,
    "/map": MapPage,
    "/config": Config,
    "/registros": Registros,
  };

  let route = currentRoute();

  function currentRoute() {
    // ejemplo: "#/map" -> "/map"
    const hash = (location.hash || "").replace(/^#/, "");
    return hash || "/";
  }

  function onHashChange() {
    route = currentRoute();
    // opcional: scroll al top
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  onMount(() => {
    window.addEventListener("hashchange", onHashChange);
    // si entrás directo sin hash, asegurá home
    if (!location.hash) location.hash = "#/";
    return () => window.removeEventListener("hashchange", onHashChange);
  });

  // componente seleccionado o 404
  $: Page = routes[route] ?? NotFound;
</script>

<svelte:component this={Page} />
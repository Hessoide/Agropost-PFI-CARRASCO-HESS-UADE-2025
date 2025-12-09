<script>
  import { onMount } from "svelte";
  import Home from "./pages/Home.svelte";
  import MapPage from "./pages/Map.svelte";
  import Registros from "./pages/Registros.svelte";
  import NotFound from "./pages/NotFound.svelte";
  import Campo from "./pages/Campo.svelte";
  import CamposGuardados from "./pages/CamposGuardados.svelte";
  import CampoMenu from "./pages/CampoMenu.svelte";
  import CampoVer from "./pages/CampoVer.svelte";
  import Maquinaria from "./pages/Maquinaria.svelte";

  // Mapea rutas -> componente
  const routes = {
    "/": Home,
    "/map": MapPage,
    "/campos": CamposGuardados,
    "/campo-menu": CampoMenu,
    "/campo-ver": CampoVer,
    "/maquinaria": Maquinaria,
    "/registros": Registros,
    "/campo": Campo,
  };

  let route = currentRoute();
  let fullHash = location.hash || "#/";  

  function currentRoute() {
    // "#/map?lat=..&lon=.." -> "/map"
    const raw = (location.hash || "#/").replace(/^#/, "");
    const pathOnly = raw.split("?")[0];      // quita query
    const normalized = pathOnly.replace(/\/+$/, "") || "/"; // quita "/" final
    return normalized;
  }

  function onHashChange() {
    fullHash = location.hash || "#/"; 
    route = currentRoute();
    // opcional: scroll al top
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  onMount(() => {
    if (!location.hash) location.hash = "#/"; // home por defecto
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  });

  // componente seleccionado o 404
  $: Page = routes[route] ?? NotFound;
</script>

{#key location.hash}
  <svelte:component this={Page} />
{/key}

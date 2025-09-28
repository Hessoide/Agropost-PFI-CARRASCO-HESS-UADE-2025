<script>
  import BackButton from "../components/BackButton.svelte";
  import { onMount } from "svelte";

  const basePath = "/campos%20guardados"; // espacio codificado

  let campos = [];
  let loading = true;
  let error = null;

  async function loadCampos() {
    const idxUrl = `${basePath}/index.json`;
    const idxRes = await fetch(idxUrl, { cache: "no-cache" });
    if (!idxRes.ok) throw new Error(`No se pudo leer ${idxUrl}`);
    const idx = await idxRes.json();
    const ids = Array.isArray(idx) ? idx : (Array.isArray(idx.campos) ? idx.campos : []);
    const list = [];
    for (const id of ids) {
      try {
        const encodedId = encodeURIComponent(id);
        const datosUrl = `${basePath}/${encodedId}/datos.json`;
        const areaUrl  = `${basePath}/${encodedId}/area.geojson`;
        const res = await fetch(datosUrl, { cache: "no-cache" });
        if (!res.ok) throw new Error(`No se pudo leer ${datosUrl}`);
        const datos = await res.json();
        list.push({ id, nombre: datos.nombre ?? id, datosUrl, areaUrl });
      } catch (e) {
        console.warn('Saltando campo con error', id, e);
      }
    }
    return list;
  }

  onMount(async () => {
    try {
      campos = await loadCampos();
    } catch (e) {
      error = e.message || String(e);
    } finally {
      loading = false;
    }
  });
</script>

<div class="ui"><BackButton /></div>

<main class="campos">
  <section class="panel">
    <h1>Seleccionar campo</h1>

    {#if loading}
      <p>Cargando…</p>
    {:else if error}
      <p class="err">{error}</p>
    {:else if !campos.length}
      <p>No hay campos guardados.</p>
    {:else}
      <ul class="lista">
        {#each campos as c}
          <li class="item">
            <div class="info">
              <strong>{c.nombre}</strong>
              <small class="id">{c.id}</small>
            </div>
            <div class="acciones">
              <a class="btn" href={`#/campo-menu?id=${encodeURIComponent(c.id)}`}>seleccionar</a>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
  
</main>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  .campos{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
  .panel{ display:grid; gap:16px; width:100%; max-width:720px; }
  .lista{ list-style:none; display:grid; gap:12px; padding:0; margin:0; }
  .item{ display:flex; justify-content:space-between; align-items:center; padding:12px; border:1px solid #ddd; border-radius:8px; }
  .info{ display:flex; flex-direction:column; gap:4px; }
  .id{ opacity:.6; }
  .acciones{ display:flex; gap:8px; }
  .btn{ padding:8px 12px; border:1px solid #aaa; border-radius:6px; text-decoration:none; }
  .err{ color:crimson; }
</style>

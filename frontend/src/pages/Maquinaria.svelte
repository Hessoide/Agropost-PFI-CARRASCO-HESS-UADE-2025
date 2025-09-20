<script>
  import BackButton from "../components/BackButton.svelte";
  import { onMount } from "svelte";

  const basePath = "/campos%20guardados"; // carpeta pública

  let id = null;
  let datosUrl = null;
  let datosBase = null;   // desde archivo
  let datos = null;       // con overrides de localStorage
  let loading = true;
  let error = null;

  let nuevoNombre = "";
  let nuevoAncho = ""; // string para input

  function lsKey(id) { return `campo:${id}:datos`; }

  function readId() {
    const qs = new URLSearchParams((location.hash.split("?")[1] || ""));
    id = qs.get("id");
    datosUrl = id ? `${basePath}/${encodeURIComponent(id)}/datos.json` : null;
  }

  function mergeDatos(base, override) {
    const o = override || {};
    return {
      nombre: o.nombre ?? base?.nombre ?? id ?? "(sin nombre)",
      maquinaria_actual: (o.maquinaria_actual ?? base?.maquinaria_actual ?? o["maquinaria actua"] ?? base?.["maquinaria actua"]) ?? null,
      maquinarias: Array.isArray(o.maquinarias) ? o.maquinarias
                  : (Array.isArray(base?.maquinarias) ? base.maquinarias : [])
    };
  }

  async function loadDatos() {
    if (!datosUrl) throw new Error("Falta id");
    const res = await fetch(datosUrl);
    if (!res.ok) throw new Error(`No se pudo leer ${datosUrl}`);
    const base = await res.json();
    datosBase = base;
    try {
      const raw = localStorage.getItem(lsKey(id));
      const over = raw ? JSON.parse(raw) : null;
      datos = mergeDatos(base, over);
    } catch {
      datos = mergeDatos(base, null);
    }
  }

  function saveDatos() {
    try { localStorage.setItem(lsKey(id), JSON.stringify({
      nombre: datos.nombre,
      maquinaria_actual: datos.maquinaria_actual,
      maquinarias: datos.maquinarias
    })); } catch {}
  }

  function setActual(nombre) {
    datos.maquinaria_actual = nombre;
    saveDatos();
  }

  function borrar(nombre) {
    datos.maquinarias = (datos.maquinarias || []).filter(m => m?.nombre !== nombre);
    if (datos.maquinaria_actual === nombre) datos.maquinaria_actual = null;
    saveDatos();
  }

  function agregar() {
    const n = (nuevoNombre || "").trim();
    const a = parseFloat(nuevoAncho);
    if (!n) { alert("Falta nombre"); return; }
    if (!Number.isFinite(a) || a <= 0) { alert("Ancho inválido"); return; }
    if ((datos.maquinarias || []).some(m => m?.nombre === n)) { alert("Ya existe una maquinaria con ese nombre"); return; }
    datos.maquinarias = [...(datos.maquinarias || []), { nombre: n, ancho: a }];
    nuevoNombre = ""; nuevoAncho = "";
    saveDatos();
  }

  onMount(async () => {
    try {
      readId();
      await loadDatos();
    } catch (e) {
      error = e.message || String(e);
    } finally {
      loading = false;
      window.addEventListener("hashchange", async () => {
        loading = true; error = null; datosBase = null; datos = null;
        readId();
        try { await loadDatos(); } catch (e) { error = e.message || String(e); }
        loading = false;
      });
    }
  });
</script>

<div class="ui"><BackButton /></div>

<main class="maq">
  <section class="panel">
    <h1>Configurar maquinaria</h1>
    {#if loading}
      <p>Cargando…</p>
    {:else if error}
      <p class="err">{error}</p>
    {:else if !id}
      <p>Falta el parámetro id del campo.</p>
    {:else}
      <p class="sub">
        Campo: <strong>{datos?.nombre ?? id}</strong> — Maquinaria actual: <strong>{datos?.maquinaria_actual ?? 'ninguna'}</strong>
      </p>

      <ul class="lista">
        {#each (datos?.maquinarias ?? []) as m}
          <li class="item">
            <div class="info">
              <strong>{m?.nombre}</strong>
              <small>{m?.ancho} m</small>
            </div>
            <div class="acciones">
              <button class="btn" on:click={() => setActual(m?.nombre)}>seleccionar</button>
              <button class="btn danger" on:click={() => borrar(m?.nombre)}>borrar</button>
            </div>
          </li>
        {/each}
        {#if !(datos?.maquinarias?.length)}
          <li class="item empty">No hay maquinarias cargadas.</li>
        {/if}
      </ul>

      <div class="agregar">
        <input class="in" placeholder="Nombre" bind:value={nuevoNombre} />
        <input class="in" placeholder="Ancho (m)" type="number" min="0" step="0.1" bind:value={nuevoAncho} />
        <button class="btn" on:click={agregar}>agregar maquinaria</button>
      </div>
    {/if}
  </section>
</main>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  .maq{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
  .panel{ display:grid; gap:16px; width:100%; max-width:720px; }
  .sub{ opacity:.8; margin:0; }
  .lista{ list-style:none; display:grid; gap:12px; padding:0; margin:0; }
  .item{ display:flex; justify-content:space-between; align-items:center; padding:12px; border:1px solid #ddd; border-radius:8px; }
  .empty{ opacity:.6; justify-content:center; }
  .info{ display:flex; flex-direction:column; gap:4px; }
  .acciones{ display:flex; gap:8px; }
  .agregar{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .in{ padding:8px 10px; border:1px solid #bbb; border-radius:6px; }
  .btn{ padding:8px 12px; border:1px solid #aaa; border-radius:6px; background:#fff; cursor:pointer; }
  .btn.danger{ border-color:#d9534f; color:#d9534f; }
  h1{ margin:0; }
</style>



<script>
  import BackButton from "../components/BackButton.svelte";
  import { onMount } from "svelte";

  let id = null;

  let mode = null;       // 'start' | 'continue' | null
  let routeName = "";
  let creating = false;
  let createError = null;

  let recorridos = [];
  let listLoading = false;
  let listLoaded = false;
  let listError = null;

  function resetState() {
    mode = null;
    routeName = "";
    creating = false;
    createError = null;
    recorridos = [];
    listLoading = false;
    listLoaded = false;
    listError = null;
  }

  async function parseErrorResponse(res) {
    try {
      const data = await res.json();
      if (data && typeof data.detail === "string") return data.detail;
      if (data && typeof data.error === "string") return data.error;
    } catch (e) {
      // ignoramos errores de parseo
    }
    return `HTTP ${res.status}`;
  }

  function readId() {
    const qs = new URLSearchParams((location.hash.split("?")[1] || ""));
    const nextId = qs.get("id");
    if (nextId !== id) {
      id = nextId;
      resetState();
    }
  }

  onMount(() => {
    readId();
    window.addEventListener("hashchange", readId);
    return () => window.removeEventListener("hashchange", readId);
  });

  function handleStartClick() {
    if (!id) return;
    mode = "start";
    routeName = "";
    createError = null;
  }

  async function fetchRecorridos() {
    if (!id) return;
    listLoading = true;
    listError = null;
    const expectedCampo = id;
    try {
      const res = await fetch(`/api/campos/${encodeURIComponent(expectedCampo)}/recorridos`);
      if (!res.ok) {
        throw new Error(await parseErrorResponse(res));
      }
      const data = await res.json();
      if (id !== expectedCampo) return;
      recorridos = Array.isArray(data && data.recorridos) ? data.recorridos : [];
      listLoaded = true;
    } catch (e) {
      if (id !== expectedCampo) return;
      listError = e.message || String(e);
    } finally {
      if (id === expectedCampo) listLoading = false;
    }
  }

  async function handleContinueClick() {
    if (!id) return;
    mode = "continue";
    if (!listLoaded && !listLoading) {
      await fetchRecorridos();
    }
  }

  function cancelMode() {
    mode = null;
    createError = null;
    routeName = "";
  }

  function openRecorrido(rec) {
    if (!rec || !rec.url || !id) return;
    const qs = new URLSearchParams();
    qs.set("campo", id);
    qs.set("geo", rec.url);
    location.hash = `#/map?${qs.toString()}`;
  }

  async function submitNewRecorrido() {
    if (!id) {
      createError = "Selecciona un campo valido.";
      return;
    }
    const nombre = routeName.trim();
    if (!nombre) {
      createError = "Elige un nombre para el recorrido.";
      return;
    }
    creating = true;
    createError = null;
    const campo = id;
    try {
      const res = await fetch(`/api/campos/${encodeURIComponent(campo)}/recorridos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre })
      });
      if (!res.ok) {
        throw new Error(await parseErrorResponse(res));
      }
      const data = await res.json();
      if (id !== campo) return;
      const rec = data && data.recorrido;
      if (rec) {
        routeName = "";
        mode = null;
        listLoaded = false;
        openRecorrido(rec);
      }
    } catch (e) {
      if (id === campo) createError = e.message || String(e);
    } finally {
      if (id === campo) creating = false;
    }
  }
</script>

<div class="ui"><BackButton /></div>

<main class="menu-campo">
  <section class="panel">
    <h1>Campo seleccionado: {id ?? '(sin id)'}</h1>

    {#if !id}
      <p>No se especifico el campo.</p>
    {:else}
      <nav class="acciones">
        <a class="btn" href={`#/maquinaria?id=${encodeURIComponent(id)}`}>configurar maquinaria</a>
        <button class="btn" type="button" on:click={handleStartClick}>iniciar recorrido</button>
        <button class="btn" type="button" on:click={handleContinueClick}>continuar recorrido</button>
        <a class="btn" href={`#/campo-ver?id=${encodeURIComponent(id)}`}>ver campo</a>
      </nav>

      {#if mode === "start"}
        <section class="subpanel">
          <h2>Iniciar nuevo recorrido</h2>
          <form class="form" on:submit|preventDefault={submitNewRecorrido}>
            <label class="field">
              <span>Nombre del recorrido</span>
              <input
                type="text"
                bind:value={routeName}
                placeholder="Ej. recorrido-primavera"
                autocomplete="off"
              />
            </label>
            {#if createError}
              <p class="err">{createError}</p>
            {/if}
            <div class="form-actions">
              <button class="btn" type="submit" disabled={creating || !routeName.trim()}>crear y abrir</button>
              <button class="btn ghost" type="button" on:click={cancelMode} disabled={creating}>cancelar</button>
            </div>
          </form>
        </section>
      {:else if mode === "continue"}
        <section class="subpanel">
          <h2>Continuar recorrido</h2>
          {#if listLoading}
            <p>Cargando recorridos...</p>
          {:else if listError}
            <p class="err">{listError}</p>
            <button class="btn" type="button" on:click={fetchRecorridos}>reintentar</button>
          {:else if !recorridos.length}
            <p>No hay recorridos guardados.</p>
          {:else}
            <ul class="lista-recorridos">
              {#each recorridos as rec}
                <li class="rec-item">
                  <div class="rec-info">
                    <strong>{rec.nombre}</strong>
                    <small>{rec.archivo}</small>
                  </div>
                  <button class="btn" type="button" on:click={() => openRecorrido(rec)}>continuar</button>
                </li>
              {/each}
            </ul>
          {/if}
        </section>
      {/if}
    {/if}
  </section>
</main>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  .menu-campo{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
  .panel{ display:grid; gap:16px; width:100%; max-width:540px; }
  .acciones{ display:flex; flex-wrap:wrap; gap:12px; }
  .btn{ padding:10px 14px; border:1px solid #aaa; border-radius:6px; text-decoration:none; background:#fff; color:#111; display:inline-flex; align-items:center; gap:6px; cursor:pointer; transition:background .15s ease; }
  .btn:hover:not(:disabled){ background:#f4f4f4; }
  .btn:disabled{ opacity:.5; cursor:not-allowed; }
  .btn.ghost{ background:transparent; }
  h1{ margin:0 0 8px; }
  h2{ margin:0; font-size:1.05rem; }
  p{ margin:0; }
  .subpanel{ border-top:1px solid #e3e3e3; padding-top:16px; display:grid; gap:14px; }
  .form{ display:grid; gap:14px; }
  .field{ display:grid; gap:6px; font-size:.95rem; }
  .field input{ padding:10px 12px; border:1px solid #bbb; border-radius:6px; font-size:1rem; }
  .form-actions{ display:flex; gap:10px; flex-wrap:wrap; }
  .lista-recorridos{ list-style:none; display:grid; gap:10px; margin:0; padding:0; }
  .rec-item{ display:flex; justify-content:space-between; align-items:center; padding:10px 14px; border:1px solid #ddd; border-radius:8px; }
  .rec-info{ display:flex; flex-direction:column; gap:4px; }
  .rec-info small{ opacity:.65; font-size:.85rem; }
  .err{ color:crimson; }
</style>

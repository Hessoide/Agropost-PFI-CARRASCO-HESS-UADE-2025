<script>
  import BackButton from "../components/BackButton.svelte";
  import { onMount } from "svelte";

  let id = null;

  function readId() {
    const qs = new URLSearchParams((location.hash.split("?")[1] || ""));
    id = qs.get("id");
  }

  onMount(() => {
    readId();
    window.addEventListener("hashchange", readId);
    return () => window.removeEventListener("hashchange", readId);
  });
</script>

<div class="ui"><BackButton /></div>

<main class="menu-campo">
  <section class="panel">
    <h1>Campo seleccionado: {id ?? '(sin id)'}</h1>

    {#if !id}
      <p>No se especificó el campo.</p>
    {:else}
      <nav class="acciones">
        <a class="btn" href={`#/maquinaria?id=${encodeURIComponent(id)}`}>configurar maquinaria</a>
        <a class="btn" href="#/map">iniciar/continuar recorrido</a>
        <a class="btn" href={`#/campo-ver?id=${encodeURIComponent(id)}`}>ver campo</a>
      </nav>
    {/if}
  </section>
</main>

<style>
  .ui{ position:fixed; top:12px; left:12px; z-index:2000; }
  .menu-campo{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
  .panel{ display:grid; gap:16px; width:100%; max-width:520px; }
  .acciones{ display:flex; flex-wrap:wrap; gap:12px; }
  .btn{ padding:10px 14px; border:1px solid #aaa; border-radius:6px; text-decoration:none; }
  h1{ margin:0 0 8px; }
  p{ margin:0; }
  </style>

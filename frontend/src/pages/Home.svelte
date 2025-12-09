<script>
  function handleNuevoCampo() {
    const nombre = window.prompt("Nombre del campo nuevo:");
    if (nombre === null) return;
    const trimmed = nombre.trim();
    if (!trimmed) return;
    const qs = new URLSearchParams();
    qs.set("nuevo", "1");
    qs.set("nombre", trimmed);
    location.hash = `#/campo?${qs.toString()}`;
  }
</script>

<main class="home">
  <section class="panel">
    <h1>AgroPost</h1>
    <nav class="menu">
      <button class="btn" type="button" on:click={handleNuevoCampo}>cargar campo nuevo</button>
      <a class="btn" href="#/campos">seleccionar campo</a>
    </nav>
  </section>
</main>

<style>
  .home{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:16px; }
  .panel{ display:grid; gap:20px; width:100%; max-width:640px; text-align:center; }
  .menu{ display:flex; gap:16px; flex-wrap:wrap; justify-content:center; width:100%; }
  .btn{ font: inherit; padding:18px 24px; border-radius:12px; border:1px solid #bfbfbf; background:#fff; color:#111; text-decoration:none; font-weight:700; min-width:240px; text-align:center; box-shadow:0 3px 8px rgba(0,0,0,0.1); display:inline-flex; align-items:center; justify-content:center; cursor:pointer; font-size:1.05rem; }
</style>

<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import * as L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import * as turf from '@turf/turf';
  import { getConfig } from './lib/config';

  export let initLat = null;
  export let initLon = null;
  export let initZoom = 18;
  export let useMock = false;

  const cfg = getConfig();
  const WS_URL = (cfg.wsUrl && cfg.wsUrl.trim()) || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;

  let mapEl, map, lineLayer, currentMarker, ws, mockTimer, dataTimeout;
  let coords = [];                   // [lon, lat]
  let points = [];                   // {ts, lat, lon, ...}
  let areaHa = '0.000';
  let fixText = '—';
  let fuente = '—';                  // SIM / WS / —
  let puntos = 0;                    // contador visible

  function log(...a){ console.log('[MAP]', ...a); }

  function addPoint(lat, lon, extra = {}) {
    if (!map) return;
    const ts  = extra.ts || new Date().toISOString();
    const fix = extra.fix ?? fixText;
    const pdop = extra.pdop ?? null;
    const sats = extra.sats ?? null;

    points.push({ ts, lat, lon, fix, pdop, sats });
    puntos = points.length;
    coords.push([lon, lat]);

    const ll = L.latLng(lat, lon);
    lineLayer.addLatLng(ll);
    if (!currentMarker) currentMarker = L.circleMarker(ll, { radius: 5 }).addTo(map);
    else currentMarker.setLatLng(ll);

    // si no vino centro inicial, centramos al primer punto real
    if (coords.length === 1 && (initLat === null || initLon === null)) {
      map.setView(ll, 18);
    }

    if (coords.length % 5 === 0) {
      const ls = turf.lineString(coords);
      const buff = turf.buffer(ls, 1.0, { units: 'meters' });
      areaHa = (turf.area(buff) / 10000).toFixed(3);
    }
  }

  function startSim() {
    if (mockTimer) return;
    const baseLat = Number.isFinite(initLat) ? initLat : cfg.defaultLat;
    const baseLon = Number.isFinite(initLon) ? initLon : cfg.defaultLon;
    let i = 0;
    mockTimer = setInterval(() => {
      const lat = baseLat + 0.00002 * Math.sin(i / 10);
      const lon = baseLon + 0.00002 * Math.cos(i / 10);
      addPoint(lat, lon, { fix: 'SIM' });
      fixText = 'SIM';
      i++;
    }, 500);
  }
  function stopSim(){ if (mockTimer){ clearInterval(mockTimer); mockTimer = null; } }

  function connectWS() {
    try {
      ws = new WebSocket(WS_URL);
      ws.onopen = () => {
        console.log('[MAP] WS conectado', WS_URL);
        // Si en 2s no llega ningún mensaje, arrancamos simulación igual (útil para test)
        clearTimeout(dataTimeout);
        dataTimeout = setTimeout(() => { if (!mockTimer) startSim(); }, 2000);
      };
      ws.onmessage = (ev) => {
        clearTimeout(dataTimeout);
        let p = {}; try { p = JSON.parse(ev.data); } catch {}
        const lat = p.lat ?? p.latitude ?? p.Lat ?? p.Latitude;
        const lon = p.lon ?? p.lng ?? p.long ?? p.longitude ?? p.Lon ?? p.Longitude;
        if (Number.isFinite(lat) && Number.isFinite(lon)) {
          const q = p.fix_quality ?? p.fix ?? 0;
          fixText = ({0:'Sin fix',1:'GPS',2:'DGPS',4:'RTK FIX',5:'RTK FLOAT'})[q] ?? `fix=${q}`;
          // Llega dato real: si querés apagar simulación, descomentá:
          // stopSim();
          addPoint(lat, lon, { ts: p.ts, fix: fixText, pdop: p.pdop, sats: p.sats });
        }
      };
      // 🔴 FALLBACK SIEMPRE (sin chequear useMock)
      ws.onerror = (e) => { console.log('[MAP] WS error', e); if (!mockTimer) startSim(); };
      ws.onclose  = () => { console.log('[MAP] WS cerrado');   if (!mockTimer) startSim(); };
    } catch (e) {
      console.log('[MAP] WS catch', e);
      if (!mockTimer) startSim();
    }
  }

  async function ensureSize() {
    await tick();
    requestAnimationFrame(() => map && map.invalidateSize(true));
    setTimeout(() => map && map.invalidateSize(), 300);
  }

  onMount(async () => {
    map = L.map(mapEl, {
      zoomControl: false, preferCanvas: true,
      zoomSnap: 0.25, zoomDelta: 0.25, minZoom: 1, maxZoom: 28
    });

    if (!cfg.offline) {
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 28 }).addTo(map);
    }
    lineLayer = L.polyline([], { weight: 4 }).addTo(map);

    // centro inicial
    const cLat = Number.isFinite(initLat) ? initLat : cfg.defaultLat;
    const cLon = Number.isFinite(initLon) ? initLon : cfg.defaultLon;
    const cZoom = Number.isFinite(initZoom) ? initZoom : cfg.defaultZoom;
    map.setView([cLat, cLon], cZoom);

    if (useMock) startSim();   // 👉 sim arranca enseguida si entraste con mock=1
    connectWS();               // 👉 y al mismo tiempo intentamos WS

    await ensureSize();
  });

  onDestroy(() => { try { ws && ws.close(); } catch {} stopSim(); map && map.remove(); });

  function recenter() {
    const pts = lineLayer.getLatLngs();
    if (pts.length) map.setView(pts[pts.length - 1], map.getZoom());
    else map.setView(map.getCenter(), map.getZoom());
  }

  // export simple (opcional, puedes mantener el que ya tenías)
  function downloadBlob(content, filename, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  }
  function exportCSV() {
    const header = "ts,lat,lon,fix,pdop,sats";
    const rows = points.map(p => [p.ts, p.lat, p.lon, p.fix ?? "", p.pdop ?? "", p.sats ?? ""].join(","));
    downloadBlob([header, ...rows].join("\n"),
      `track_${new Date().toISOString().replace(/[:.]/g,'-')}.csv`, "text/csv");
  }
</script>

<div class="wrap">
  <div class="map" bind:this={mapEl}></div>

  <div class="hud">
    <div>Fuente: {fuente}</div>
    <div>Fix: {fixText}</div>
    <div>Puntos: {puntos}</div>
    <div>Área: {areaHa} ha</div>
    <button class="btn" on:click={recenter}>Recentrar</button>
    <button class="btn" on:click={exportCSV}>CSV</button>
  </div>
</div>

<style>
  .wrap { position: relative; width: 100%; height: 100%; }
  .map  { position: absolute; inset: 0; }
  .hud  { position:absolute; top:10px; left:10px; background:#0009; color:#fff; padding:8px; border-radius:8px; display:flex; gap:10px; z-index:1500;}
  .btn  { padding:.6rem .9rem; border:1px solid #ccc; border-radius:.5rem; background:#fff; color:#111; cursor:pointer; }
</style>
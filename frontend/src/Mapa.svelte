<script>
  import { onMount } from 'svelte';
  import * as L from 'leaflet';
  import 'leaflet/dist/leaflet.css';
  import * as turf from '@turf/turf';

  let map, lineLayer;
  let coords = [];               // [lon, lat]
  let areaHa = '0.000';
  let fixText = '—';
  const wsUrl = `ws://${location.host}/ws`;   // backend FastAPI

  function addPoint(lat, lon) {
    if (!map) return;
    coords.push([lon, lat]);
    lineLayer.addLatLng([lat, lon]);

    if (coords.length === 1) map.setView([lat, lon], 18);

    if (coords.length % 5 === 0) {
      const ls = turf.lineString(coords);
      const buff = turf.buffer(ls, 1.0, { units: 'meters' }); // ancho/2 (ajustar)
      areaHa = (turf.area(buff) / 10000).toFixed(3);
    }
  }

  function startSim() {
    let i = 0, base = [-34.6, -58.4];
    setInterval(() => {
      const lat = base[0] + 0.0001 * Math.sin(i / 20);
      const lon = base[1] + 0.0001 * Math.cos(i / 20);
      addPoint(lat, lon);
      fixText = 'SIM';
      i++;
    }, 1000);
  }

  onMount(() => {
    // inicializar mapa
    map = L.map('map', { zoomControl: false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
    lineLayer = L.polyline([], { weight: 4 }).addTo(map);

    // conectar WebSocket
    try {
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => console.log('WS conectado:', wsUrl);
      ws.onmessage = (ev) => {
        const p = JSON.parse(ev.data);
        if (Number.isFinite(p.lat) && Number.isFinite(p.lon)) {
          addPoint(p.lat, p.lon);
          const q = p.fix_quality ?? 0;
          fixText = ({0:'Sin fix',1:'GPS',2:'DGPS',4:'RTK FIX',5:'RTK FLOAT'})[q] ?? `fix=${q}`;
        }
      };
      ws.onerror = () => { console.warn('WS error, simulando'); startSim(); };
      ws.onclose  = () => { console.warn('WS cerrado, simulando'); startSim(); };
    } catch (e) {
      console.warn('No se pudo abrir WS, simulando', e);
      startSim();
    }
  });
</script>

<div id="map" style="position:absolute; inset:0 0 64px 0;"></div>

<div class="hud">
  <div>Fix: {fixText}</div>
  <div>Área: {areaHa} ha</div>
  <button on:click={() => map && map.locate({ setView: true, maxZoom: 18 })}>
    Centrar
  </button>
</div>

<style>
  .hud{
    position:absolute; top:10px; left:10px;
    background:#0009; color:#fff; padding:8px;
    border-radius:8px; font:14px system-ui;
  }
  button{ min-width:48px; min-height:32px; border:none; border-radius:8px; }
</style>

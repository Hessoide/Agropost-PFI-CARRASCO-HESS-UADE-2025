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
  export let minimal = false;   // modo minimal: solo mapa base
  export let noTiles = false;   // no cargar capa de tiles base
  export let geoUrl = null;     // si se pasa, cargar este GeoJSON
  export let showScale = false; // muestra cÃ­rculo de escala (radio)
  export let showGrid = false;  // muestra cuadrÃ­cula tipo ajedrez basada en la escala

  export let campoId = null;

  const cfg = getConfig();
  const WS_URL = (cfg.wsUrl && cfg.wsUrl.trim()) || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;

  let mapEl, map, lineLayer, currentMarker, ws;
  let gridCanvas;               // canvas para cuadrÃ­cula
  let overlayGeoJSONLayer; // capa cargada desde un archivo GeoJSON
  let routeGroup;          // grupo para puntos del recorrido
  let routeLine;           // lÃ­nea que conecta los puntos del recorrido

  let coords = [];                   // [lon, lat]
  let points = [];                   // {ts, lat, lon, ...}
  let areaHa = '0.000';
  let fixText = '';
  let fuente = '';
  let puntos = 0;                    // contador visible
  let lastPdop = null;
  let lastSats = null;
  let scalePx = 0;                   // radio en pÃ­xeles
  let scaleMeters = 0;               // longitud de línea en metros
  let gridOriginLL = null;

  let coverageLayer;                 // poligono de cobertura dinamico
  let maquinariaActual = null;
  let maquinariaAncho = null;
  let campoDatosVersion = 0;
  let lastCampoIdLoaded = undefined;
  let totalAreaM2 = 0;

  const CAMPOS_BASE = "/campos%20guardados";

  function datosLsKey(id) {
    return `campo:${id}:datos`;
  }

  function mergeCampoDatos(id, base, override) {
    const b = base || {};
    const o = override || {};
    const maquinariaAct =
      (o.maquinaria_actual ?? b.maquinaria_actual ?? o["maquinaria actua"] ?? b["maquinaria actua"]) ?? null;
    const maqs = Array.isArray(o.maquinarias)
      ? o.maquinarias
      : (Array.isArray(b.maquinarias) ? b.maquinarias : []);
    return {
      nombre: o.nombre ?? b.nombre ?? id ?? "(sin nombre)",
      maquinaria_actual: maquinariaAct,
      maquinarias: maqs
    };
  }

  function clearCoverage(resetArea = false) {
    if (coverageLayer) {
      try { coverageLayer.clearLayers(); } catch {}
      try { coverageLayer.remove(); } catch {}
    }
    coverageLayer = null;
    totalAreaM2 = 0;
    if (resetArea) areaHa = '0.000';
  }

  function updateFallbackArea() {
    if (coords.length >= 2) {
      try {
        const ls = turf.lineString(coords);
        const buff = turf.buffer(ls, 1.0, { units: 'meters' });
        areaHa = (turf.area(buff) / 10000).toFixed(3);
      } catch {}
    } else {
      areaHa = '0.000';
    }
  }

  function addCoverageSegment(prevCoord, currCoord) {
    if (!map || minimal) return;
    if (!maquinariaAncho || maquinariaAncho <= 0) return;

    const prevPt = turf.point(prevCoord);
    const currPt = turf.point(currCoord);
    const segmentMeters = turf.distance(prevPt, currPt, { units: 'meters' });
    if (!Number.isFinite(segmentMeters) || segmentMeters <= 0) return;

    const bearing = turf.rhumbBearing(prevPt, currPt);
    const halfWidth = maquinariaAncho / 2;

    const prevLeft = turf.rhumbDestination(prevPt, halfWidth, bearing - 90, { units: 'meters' }).geometry.coordinates;
    const prevRight = turf.rhumbDestination(prevPt, halfWidth, bearing + 90, { units: 'meters' }).geometry.coordinates;
    const currLeft = turf.rhumbDestination(currPt, halfWidth, bearing - 90, { units: 'meters' }).geometry.coordinates;
    const currRight = turf.rhumbDestination(currPt, halfWidth, bearing + 90, { units: 'meters' }).geometry.coordinates;

    if (!coverageLayer) coverageLayer = L.layerGroup().addTo(map);

    L.polygon(
      [
        [prevLeft[1], prevLeft[0]],
        [currLeft[1], currLeft[0]],
        [currRight[1], currRight[0]],
        [prevRight[1], prevRight[0]]
      ],
      {
        color: '#2e7d32',
        weight: 0,
        opacity: 0,
        fillColor: '#66bb6a',
        fillOpacity: 0.45
      }
    ).addTo(coverageLayer);

    totalAreaM2 += maquinariaAncho * segmentMeters;
    areaHa = (totalAreaM2 / 10000).toFixed(3);
  }

  function rebuildCoverageFromCoords() {
    clearCoverage(true);
    if (!map || minimal) return;

    if (!maquinariaAncho || maquinariaAncho <= 0) {
      updateFallbackArea();
      return;
    }
    if (coords.length < 2) {
      areaHa = '0.000';
      return;
    }
    coverageLayer = L.layerGroup().addTo(map);
    totalAreaM2 = 0;
    for (let i = 1; i < coords.length; i += 1) {
      addCoverageSegment(coords[i - 1], coords[i]);
    }
  }


  async function loadCampoConfig(id) {
    const version = ++campoDatosVersion;
    if (!id) {
      maquinariaActual = null;
      maquinariaAncho = null;
      clearCoverage(true);
      updateFallbackArea();
      return;
    }
    try {
      const encoded = encodeURIComponent(id);
      const url = `${CAMPOS_BASE}/${encoded}/datos.json`;
      const res = await fetch(url, { cache: 'no-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const base = await res.json();
      let override = null;
      try {
        if (typeof localStorage !== 'undefined') {
          const raw = localStorage.getItem(datosLsKey(id));
          override = raw ? JSON.parse(raw) : null;
        }
      } catch {
        override = null;
      }
      if (version !== campoDatosVersion) return;
      const datos = mergeCampoDatos(id, base, override);
      maquinariaActual = datos.maquinaria_actual ?? null;
      const selected = (datos.maquinarias || []).find(m => (m?.nombre ?? null) === maquinariaActual);
      const widthValue = selected?.ancho;
      const widthNumber = Number(widthValue);
      maquinariaAncho = Number.isFinite(widthNumber) && widthNumber > 0 ? widthNumber : null;
      if (maquinariaAncho && maquinariaAncho > 0) {
        rebuildCoverageFromCoords();
      } else {
        clearCoverage(true);
        updateFallbackArea();
      }
    } catch (e) {
      if (version !== campoDatosVersion) return;
      console.warn('[MAP] No se pudo cargar maquinaria del campo', e);
      maquinariaActual = null;
      maquinariaAncho = null;
      clearCoverage(true);
      updateFallbackArea();
    }
  }

           // origen de cuadrÃ­cula (centro del polÃ­gono si hay)

  function addPoint(lat, lon, extra = {}) {
    if (!map || minimal) return;
    const ts  = extra.ts || new Date().toISOString();
    const fix = extra.fix ?? fixText;
    const pdop = extra.pdop ?? null;
    const sats = extra.sats ?? null;

    const prevCoord = coords.length ? coords[coords.length - 1] : null;
    const newCoord = [lon, lat];

    points.push({ ts, lat, lon, fix, pdop, sats });
    puntos = points.length;
    lastPdop = pdop;
    lastSats = sats;
    coords.push(newCoord);

    if (maquinariaAncho && maquinariaAncho > 0 && prevCoord) {
      addCoverageSegment(prevCoord, newCoord);
    } else if (!maquinariaAncho || maquinariaAncho <= 0) {
      if (coords.length >= 2 && coords.length % 5 === 0) {
        updateFallbackArea();
      }
    }

    const ll = L.latLng(lat, lon);
    lineLayer.addLatLng(ll);
    if (!currentMarker) currentMarker = L.circleMarker(ll, { radius: 5 }).addTo(map);
    else currentMarker.setLatLng(ll);

    if (coords.length === 1 && (initLat === null || initLon === null)) {
      map.setView(ll, 18);
    }
  }

  $: if (campoId !== lastCampoIdLoaded) {
    lastCampoIdLoaded = campoId;
    loadCampoConfig(campoId);
  }


  function connectWS() {
    if (minimal || useMock) return; // en mock no conectamos ni simulamos
    try {
      ws = new WebSocket(WS_URL);
      fuente = 'WS';
      ws.onopen = () => {
        console.log('[MAP] WS conectado', WS_URL);
      };
      ws.onmessage = (ev) => {
        let p = {}; try { p = JSON.parse(ev.data); } catch {}
        const lat = p.lat ?? p.latitude ?? p.Lat ?? p.Latitude;
        const lon = p.lon ?? p.lng ?? p.long ?? p.longitude ?? p.Lon ?? p.Longitude;
        if (Number.isFinite(lat) && Number.isFinite(lon)) {
          const q = p.fix_quality ?? p.fix ?? 0;
          fixText = ({0:'Sin fix',1:'GPS',2:'DGPS',4:'RTK FIX',5:'RTK FLOAT'})[q] ?? `fix=${q}`;
          addPoint(lat, lon, { ts: p.ts, fix: fixText, pdop: p.pdop, sats: p.sats });
        }
      };
      ws.onerror = (e) => { console.log('[MAP] WS error', e); };
      ws.onclose  = () => { console.log('[MAP] WS cerrado'); };
    } catch (e) {
      console.log('[MAP] WS catch', e);
    }
  }

  async function ensureSize() {
    await tick();
    requestAnimationFrame(() => map && map.invalidateSize(true));
    setTimeout(() => map && map.invalidateSize(), 300);
    updateScale();
    updateGrid();
  }

  onMount(async () => {
    map = L.map(mapEl, {
      zoomControl: false, preferCanvas: true,
      zoomSnap: 0.25, zoomDelta: 0.25, minZoom: 1, maxZoom: 28
    });

    if (!cfg.offline && !noTiles) {
      const cartoUrl = 'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png';
      const cartoAttrib = '&copy; OpenStreetMap contributors &copy; CARTO';
      L.tileLayer(cartoUrl, { attribution: cartoAttrib, subdomains: 'abcd', maxNativeZoom: 20, maxZoom: 28, detectRetina: true }).addTo(map);
    }
    if (!minimal) {
      lineLayer = L.polyline([], { weight: 2, color: '#ff6a00', opacity: 0.6 }).addTo(map);
    }

    // centro inicial
    const cLat = Number.isFinite(initLat) ? initLat : cfg.defaultLat;
    const cLon = Number.isFinite(initLon) ? initLon : cfg.defaultLon;
    const cZoom = Number.isFinite(initZoom) ? initZoom : cfg.defaultZoom;
    map.setView([cLat, cLon], cZoom);

    if (!minimal) {
      // En modo mock no conectamos WS ni simulamos.
      if (useMock) {
        fuente = 'SimulaciÃ³n';
      } else {
        connectWS();
      }
    }

    // Si nos pasaron un GeoJSON directo, lo cargamos
    if (geoUrl) {
      try {
        await loadSimGeoJSON(geoUrl);
        fuente = 'GeoJSON';
      } catch (e) {
        console.warn('[MAP] No se pudo cargar', geoUrl, e);
      }
    }

    // Capa para el recorrido (puntos + lÃ­nea)
    routeGroup = L.layerGroup().addTo(map);
    routeLine = L.polyline([], { color: '#ff6a00', weight: 3 }).addTo(routeGroup);

    // Si es simulaciÃ³n, intentamos cargar GeoJSONs (pueden estar vacÃ­os)
    if (useMock) {
      try {
        await loadSimGeoJSON('/geo/simulacion.geojson');
        await loadRouteGeoJSON('/geo/recorrido.geojson');
      } catch (e) {
        console.warn('[MAP] GeoJSONs de simulaciÃ³n no disponibles', e);
      }
    }

    rebuildCoverageFromCoords();

    await ensureSize();
    try { window.addEventListener('resize', ensureSize); } catch {}

    if (showScale || showGrid) {
      try {
        map.on('move', scheduleRaf);
        map.on('zoom', scheduleRaf);
        map.on('moveend', scheduleRaf);
        map.on('zoomend', scheduleRaf);
      } catch {}
      scheduleRaf();
    }

    // Helpers globales para pruebas rÃ¡pidas en consola
    try { window.__addRoutePoint = addRoutePoint; window.__loadGeoJSON = loadSimGeoJSON; } catch {}
  });

  onDestroy(() => {
    try { ws && ws.close(); } catch {}
    try { clearCoverage(); } catch {}
    try { window.removeEventListener('resize', ensureSize); } catch {}
    try { map && map.off('move', scheduleRaf); } catch {}
    try { map && map.off('zoom', scheduleRaf); } catch {}
    try { map && map.off('moveend', scheduleRaf); } catch {}
    try { map && map.off('zoomend', scheduleRaf); } catch {}
    try { raf && cancelAnimationFrame(raf); } catch {}
    map && map.remove();
  });

  function recenter() {
    const trackPts = lineLayer?.getLatLngs?.() ?? [];
    const routePts = routeLine?.getLatLngs?.() ?? [];
    const last = routePts.length ? routePts[routePts.length - 1] : (trackPts.length ? trackPts[trackPts.length - 1] : null);
    if (last) map.setView(last, map.getZoom()); else map.setView(map.getCenter(), map.getZoom());
  }

  // Cargar y mostrar una capa GeoJSON en el mapa
  async function loadSimGeoJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (overlayGeoJSONLayer) overlayGeoJSONLayer.remove();
    overlayGeoJSONLayer = L.geoJSON(data, {
      style: f => ({ color: '#2c7fb8', weight: 2, fillColor: '#7fcdbb', fillOpacity: 0.2 }),
      pointToLayer: (feat, latlng) => L.circleMarker(latlng, { radius: 5, color: '#2c7fb8', fillColor: '#7fcdbb', fillOpacity: 0.9 })
    }).addTo(map);
    try {
      const b = overlayGeoJSONLayer.getBounds?.();
      if (b && b.isValid && b.isValid()) map.fitBounds(b, { maxZoom: 17 });
    } catch {}

    // establecer origen de cuadrÃ­cula en el centro del polÃ­gono/geojson
    try {
      const c = turf.centerOfMass(data);
      const coords = c?.geometry?.coordinates; // [lon, lat]
      if (coords && Number.isFinite(coords[0]) && Number.isFinite(coords[1])) {
        gridOriginLL = L.latLng(coords[1], coords[0]);
        updateGrid();
      }
    } catch {}
  }

  // Cargar puntos del recorrido desde un GeoJSON (FeatureCollection con Points o LineString)
  async function loadRouteGeoJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    try {
      const feats = data?.features ?? [];
      for (const f of feats) {
        const g = f?.geometry;
        if (!g) continue;
        if (g.type === 'Point') {
          const [lon, lat] = g.coordinates;
          addRoutePoint(lat, lon);
        } else if (g.type === 'LineString') {
          for (const [lon, lat] of g.coordinates) addRoutePoint(lat, lon);
        }
      }
    } catch {}
  }

  // API pÃºblica: agregar un punto al recorrido
  export function addRoutePoint(lat, lon) {
    if (!map) return;
    if (!routeGroup) routeGroup = L.layerGroup().addTo(map);
    if (!routeLine) routeLine = L.polyline([], { color: '#ff6a00', weight: 3 }).addTo(routeGroup);
    const ll = L.latLng(lat, lon);
    L.circleMarker(ll, { radius: 4, color: '#ff6a00', fillColor: '#ffb380', fillOpacity: 0.9 }).addTo(routeGroup);
    routeLine.addLatLng(ll);
  }

  // export simple (opcional)
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

  // Escala circular dinÃ¡mica
  function fmtMeters(m) {
    if (m >= 1000) {
      const km = m / 1000;
      const val = km >= 10 ? Math.round(km) : Math.round(km * 10) / 10;
      return `${val} km`;
    }
    if (m < 1) {
      const cm = Math.round(m * 100);
      return `${cm} cm`;
    }
    // metros: 1, 2, 5, 10...
    return `${m} m`;
  }

  function updateScale() {
    if (!showScale || !map) return;
    const center = map.getCenter();
    const p1 = map.latLngToContainerPoint(center);
    const p2 = L.point(p1.x + 100, p1.y);
    const ll2 = map.containerPointToLatLng(p2);
    const metersPerPx = map.distance(center, ll2) / 100;
    if (!Number.isFinite(metersPerPx) || metersPerPx <= 0) return;

    const candidates = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000];
    const desiredPx = 40;
    const minPx = 12, maxPx = 80;
    let best = candidates[0];
    let bestScore = Infinity;
    for (const m of candidates) {
      const rp = m / metersPerPx;
      const inRange = rp >= minPx && rp <= maxPx;
      const score = (inRange ? 0 : Math.min(Math.abs(rp - minPx), Math.abs(rp - maxPx))) + Math.abs(rp - desiredPx) * 0.01;
      if (score < bestScore) { bestScore = score; best = m; }
    }
    scaleMeters = best;
    scalePx = Math.max(4, best / metersPerPx);
    // actualizar grid si depende de scale
    updateGrid();
  }

  // Dibuja la cuadrÃ­cula tipo ajedrez con celdas de lado = scaleMeters
  function updateGrid() {
    if (!showGrid || !map || !gridCanvas) return;
    const dpr = (window.devicePixelRatio || 1);
    const rect = gridCanvas.parentElement?.getBoundingClientRect?.() || { width: 0, height: 0 };
    const w = Math.max(0, Math.floor(rect.width));
    const h = Math.max(0, Math.floor(rect.height));
    if (gridCanvas.width !== Math.floor(w * dpr) || gridCanvas.height !== Math.floor(h * dpr)) {
      gridCanvas.width = Math.floor(w * dpr);
      gridCanvas.height = Math.floor(h * dpr);
      gridCanvas.style.width = w + 'px';
      gridCanvas.style.height = h + 'px';
    }
    const ctx = gridCanvas.getContext('2d');
    if (!ctx || w === 0 || h === 0) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    // calcular tamaÃ±o en px de la celda a partir de scaleMeters
    const center = map.getCenter();
    const p1 = map.latLngToContainerPoint(center);
    const p2 = L.point(p1.x + 100, p1.y);
    const ll2 = map.containerPointToLatLng(p2);
    const metersPerPx = map.distance(center, ll2) / 100;
    if (!Number.isFinite(metersPerPx) || metersPerPx <= 0) return;

    // si aÃºn no hay escala calculada, generar una por defecto
    let cellMeters = scaleMeters || 10;
    const minPx = 12, maxPx = 120;
    let cellPx = cellMeters / metersPerPx;
    if (cellPx < minPx || cellPx > maxPx) {
      // adapta cellMeters a rango visual usando misma lÃ³gica de candidates
      const candidates = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];
      let best = candidates[0], bestDiff = Infinity;
      for (const m of candidates) {
        const px = m / metersPerPx;
        const diff = Math.abs(px - 40) + (px < minPx ? (minPx - px) : (px > maxPx ? (px - maxPx) : 0));
        if (diff < bestDiff) { bestDiff = diff; best = m; cellPx = px; }
      }
      cellMeters = best;
    }

    // alinear con un origen fijo (centro del polÃ­gono si hay; si no, cfg.default)
    const originLL = gridOriginLL || L.latLng(cfg.defaultLat, cfg.defaultLon);
    const ref = map.latLngToContainerPoint(originLL);
    const mod = (a,b) => ((a % b) + b) % b;
    const offX = mod(-ref.x, cellPx);
    const offY = mod(-ref.y, cellPx);

    // Ã­ndices base en metros respecto del origen para paridad estable
    const xMetersAtLeft = -ref.x * metersPerPx;
    const yMetersAtTop  = -ref.y * metersPerPx;
    const xiBase = Math.floor(xMetersAtLeft / cellMeters);
    const yiBase = Math.floor(yMetersAtTop / cellMeters);

    // dibujar tablero de ajedrez (sin costuras, usando redondeos por segmento)
    ctx.save();
    const c1 = 'rgba(255,255,255,0.20)';
    const c2 = 'rgba(255,255,255,0.06)';
    let j = 0;
    for (let y = -offY; y < h; y += cellPx, j++) {
      const y0 = Math.round(y);
      const y1 = Math.round(Math.min(h, y + cellPx));
      const yh = Math.max(1, y1 - y0);
      let i = 0;
      for (let x = -offX; x < w; x += cellPx, i++) {
        const even = (((xiBase + i) + (yiBase + j)) % 2) === 0;
        ctx.fillStyle = even ? c1 : c2;
        const x0 = Math.round(x);
        const x1 = Math.round(Math.min(w, x + cellPx));
        const ww = Math.max(1, x1 - x0);
        ctx.fillRect(x0, y0, ww, yh);
      }
    }
    ctx.restore();
  }

  // Scheduler rAF para agrupar updates en un frame
  let raf = 0, rafPending = false;
  function scheduleRaf() {
    if (rafPending) return;
    rafPending = true;
    raf = requestAnimationFrame(() => {
      rafPending = false;
      updateScale();
      updateGrid();
    });
  }
</script>

<div class="wrap">
  <div class="map" bind:this={mapEl}></div>
  {#if showGrid}
    <canvas class="grid" bind:this={gridCanvas}></canvas>
  {/if}

  {#if !minimal}
    <div class="hud">
      <div>Fuente: {fuente}</div>
      <div>Fix: {fixText}</div>
      <div>Puntos: {puntos}</div>
      <div>Area: {areaHa} ha</div>
      <div>Maquinaria: {maquinariaActual ?? "ninguna"}</div>
      <div>Ancho activo: {maquinariaAncho ? `${maquinariaAncho} m` : "sin dato"}</div>
      {#if lastPdop != null}
        <div>PDOP: {lastPdop}</div>
      {/if}
      {#if lastSats != null}
        <div>Sats: {lastSats}</div>
      {/if}
      <button class="btn" on:click={recenter}>Recentrar</button>
      <button class="btn" on:click={exportCSV}>CSV</button>
    </div>
  {/if}
  {#if showScale}
    <div class="scale-overlay">
      <div class="scale-line" style={`width:${scalePx}px;`}></div>
      <div class="scale-label">{fmtMeters(scaleMeters)}</div>
    </div>
  {/if}
</div>

<style>
  .wrap { position: relative; width: 100%; height: 100%; }
  .map  { position: absolute; inset: 0; }
  .hud  { position:absolute; top:10px; left:72px; background:#0009; color:#fff; padding:8px 12px; border-radius:8px; display:flex; gap:10px; z-index:1500; }
  .btn  { padding:.6rem .9rem; border:1px solid #ccc; border-radius:.5rem; background:#fff; color:#111; cursor:pointer; }

  .grid { position:absolute; inset:0; pointer-events:none; z-index:900; }
  .scale-overlay { position:absolute; inset:0; pointer-events:none; z-index:1500; }
  .scale-line    { position:absolute; left:10px; bottom:14px; height:4px; background:#fff; box-shadow:0 0 0 2px #0008 inset, 0 0 2px #0008; border-radius:2px; }
  .scale-label   { position:absolute; left:10px; bottom:22px; color:#fff; text-shadow: 0 1px 2px #000; font-weight:600; }
</style>

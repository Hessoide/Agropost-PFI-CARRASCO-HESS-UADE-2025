const KEY = "agropost.config.v1";

export const defaults = {
  wsUrl: "",                     // vacío = usar ws://<host>/ws
  defaultLat: -34.6037,
  defaultLon: -58.3816,
  defaultZoom: 18,
  offline: false,                // sin tiles
  showGrid: true                 // mostrar cuadrícula
};

export function getConfig() {
  try {
    const raw = localStorage.getItem(KEY);
    const saved = raw ? JSON.parse(raw) : {};
    return { ...defaults, ...saved };
  } catch {
    return { ...defaults };
  }
}

export function saveConfig(cfg) {
  localStorage.setItem(KEY, JSON.stringify(cfg));
}
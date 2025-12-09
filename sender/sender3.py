#!/usr/bin/env python3
"""
Sender3: recorre en pasadas paralelas un círculo de radio configurable (por defecto 50 m)
para cubrirlo con ancho de labor dado (por defecto 8 m) y postea a /api/pos.
"""
import argparse
import math
import time
from datetime import datetime, timezone

import requests


def post_pos(host: str, port: int, lat: float, lon: float, fix: int | None = 4, pdop: float | None = None, sats: int | None = None):
  url = f"http://{host}:{port}/api/pos"
  payload = {
      "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
      "lat": float(lat),
      "lon": float(lon),
      "fix_quality": fix,
      "pdop": pdop,
      "sats": sats,
  }
  r = requests.post(url, json=payload, timeout=5)
  r.raise_for_status()
  return r.json()


def meters_to_deg_xy(x_m: float, y_m: float, at_lat: float):
  # x_m hacia el Este, y_m hacia el Norte
  dlat = y_m / 111_320.0
  dlon = x_m / (111_320.0 * max(0.1, math.cos(math.radians(at_lat))))
  return dlat, dlon


def build_lawnmower_points(center_lat: float, center_lon: float, radius_m: float, width_m: float, step_m: float):
  """Genera puntos en pasadas E-O dentro del círculo."""
  if width_m <= 0:
    width_m = 8.0
  if step_m <= 0:
    step_m = width_m / 2.0

  points = []
  # desplazamiento x (Este-Oeste) de -r a r
  x = -radius_m
  stripe = 0
  while x <= radius_m:
    chord_half = math.sqrt(max(radius_m * radius_m - x * x, 0.0))
    y_start, y_end = -chord_half, chord_half
    # zig-zag alternando sentido
    if stripe % 2 == 0:
      y_values = frange(y_start, y_end, step_m)
    else:
      y_values = frange(y_end, y_start, -step_m)

    for y in y_values:
      dlat, dlon = meters_to_deg_xy(x, y, center_lat)
      points.append((center_lat + dlat, center_lon + dlon))
    # Asegurar que terminamos exactamente en el extremo correspondiente al sentido de la pasada
    target_end = y_values[-1] if y_values else y_end
    if (abs(target_end - y_end) > 1e-9 and stripe % 2 == 0) or (stripe % 2 == 1 and abs(target_end - y_start) > 1e-9):
      end_y = y_end if stripe % 2 == 0 else y_start
      dlat, dlon = meters_to_deg_xy(x, end_y, center_lat)
      points.append((center_lat + dlat, center_lon + dlon))

    x += width_m
    stripe += 1
  return points


def frange(start: float, stop: float, step: float):
  if step == 0:
    return []
  vals = []
  cur = start
  if step > 0:
    while cur <= stop:
      vals.append(cur)
      cur += step
  else:
    while cur >= stop:
      vals.append(cur)
      cur += step
  return vals


def cmd_lawn(args):
  host, port = args.host, args.port
  center_lat, center_lon = float(args.lat), float(args.lon)
  radius = float(args.radius)
  width = float(args.width)
  step = float(args.step)
  rate = float(args.rate)
  wait = 1.0 / rate if rate > 0 else 0

  path = build_lawnmower_points(center_lat, center_lon, radius, width, step)
  print(f"Recorriendo círculo r={radius}m con pasadas de {width}m, puntos={len(path)}, host={host}:{port}")
  sent = 0
  try:
    while True:
      for lat, lon in path:
        resp = post_pos(host, port, lat, lon, fix=args.fix, pdop=args.pdop, sats=args.sats)
        sent += 1
        print(f"[{sent}] -> {lat:.7f}, {lon:.7f} delivered={resp.get('delivered')}")
        if wait:
          time.sleep(wait)
      if not args.loop:
        break
  except KeyboardInterrupt:
    print("bye")
  except Exception as e:
    print("ERR:", e)
    time.sleep(1.0)


def main():
  p = argparse.ArgumentParser(description="AgroPost sender3: cobertura en pasadas paralelas")
  p.add_argument("--host", default="127.0.0.1", help="host del backend (IP en la LAN)")
  p.add_argument("--port", type=int, default=8000, help="puerto del backend")
  p.add_argument("--lat", type=float, default=-34.6037, help="latitud centro")
  p.add_argument("--lon", type=float, default=-58.3816, help="longitud centro")
  p.add_argument("--radius", type=float, default=50.0, help="radio del círculo (m)")
  p.add_argument("--width", type=float, default=8.0, help="ancho de labor (m) entre pasadas")
  p.add_argument("--step", type=float, default=2.0, help="separación entre puntos (m) sobre cada pasada")
  p.add_argument("--rate", type=float, default=5.0, help="puntos por segundo")
  p.add_argument("--fix", type=int, default=4, help="fix_quality (opcional)")
  p.add_argument("--pdop", type=float, default=None, help="PDOP opcional")
  p.add_argument("--sats", type=int, default=None, help="satelites opcional")
  p.add_argument("--loop", action="store_true", help="repetir el recorrido")
  p.set_defaults(func=cmd_lawn)

  args = p.parse_args()
  args.func(args)


if __name__ == "__main__":
  main()

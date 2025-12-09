#!/usr/bin/env python3
"""
Sender sencillo que dibuja un círculo de radio configurable (por defecto 50 m)
en ~30 segundos hacia /api/pos del backend.
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


def meters_to_deg(radius_m: float, at_lat: float):
  # Aproximacion: 1 deg lat ~ 111,320 m; lon escala con cos(lat)
  dlat = radius_m / 111_320.0
  dlon = radius_m / (111_320.0 * max(0.1, math.cos(math.radians(at_lat))))
  return dlat, dlon


def cmd_circle(args):
  host, port = args.host, args.port
  center_lat, center_lon = float(args.lat), float(args.lon)
  radius_m = float(args.radius)
  duration = float(args.seconds)
  rate = float(args.rate)
  wait = 1.0 / rate if rate > 0 else 0

  points = max(8, int(round(duration * rate)))
  dlat_deg, dlon_deg = meters_to_deg(radius_m, center_lat)

  print(f"Enviando circulo r={radius_m}m en ~{duration}s ({points} puntos) hacia {host}:{port}")
  sent = 0
  try:
    while True:
      for i in range(points):
        angle = 2.0 * math.pi * i / points
        lat = center_lat + dlat_deg * math.cos(angle)
        lon = center_lon + dlon_deg * math.sin(angle)
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
  p = argparse.ArgumentParser(description="AgroPost sender2: círculo fijo hacia /api/pos")
  p.add_argument("--host", default="127.0.0.1", help="host del backend (IP en la LAN)")
  p.add_argument("--port", type=int, default=8000, help="puerto del backend")
  p.add_argument("--lat", type=float, default=-34.6037, help="latitud centro del circulo")
  p.add_argument("--lon", type=float, default=-58.3816, help="longitud centro del circulo")
  p.add_argument("--radius", type=float, default=50.0, help="radio del circulo en metros")
  p.add_argument("--seconds", type=float, default=30.0, help="tiempo aproximado para completar la vuelta")
  p.add_argument("--rate", type=float, default=10.0, help="puntos por segundo")
  p.add_argument("--fix", type=int, default=4, help="fix_quality (opcional)")
  p.add_argument("--pdop", type=float, default=None, help="PDOP opcional")
  p.add_argument("--sats", type=int, default=None, help="satelites opcional")
  p.add_argument("--loop", action="store_true", help="repetir el circulo indefinidamente")
  p.set_defaults(func=cmd_circle)

  args = p.parse_args()
  args.func(args)


if __name__ == "__main__":
  main()

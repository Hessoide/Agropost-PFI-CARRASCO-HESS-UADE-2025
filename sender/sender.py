#!/usr/bin/env python3
import argparse, json, math, time
from datetime import datetime, timezone
from pathlib import Path
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


def cmd_health(args):
    url = f"http://{args.host}:{args.port}/api/health"
    r = requests.get(url, timeout=3)
    print("GET", url, r.status_code, r.text)


def cmd_simulate(args):
    host, port = args.host, args.port
    lat, lon = float(args.lat), float(args.lon)
    step = float(args.meters)  # metros entre puntos
    rate = float(args.rate)
    wait = 1.0 / rate if rate > 0 else 0
    bearing = 0.0

    print(f"Simulando desde lat={lat}, lon={lon} paso={step}m rate={rate}Hz hacia {host}:{port}")
    while True:
        try:
            # avanza en línea y gira suavemente
            dlat, dlon = meters_to_deg(step, lat)
            lat += dlat * math.cos(math.radians(bearing))
            lon += dlon * math.sin(math.radians(bearing))
            bearing = (bearing + 7) % 360
            resp = post_pos(host, port, lat, lon, fix=args.fix, pdop=args.pdop, sats=args.sats)
            print("->", lat, lon, resp.get("delivered"))
            if wait: time.sleep(wait)
        except KeyboardInterrupt:
            print("bye")
            return
        except Exception as e:
            print("ERR:", e)
            time.sleep(1.0)


def meters_to_deg(meters: float, at_lat: float):
    # aproximación: 1° lat ~ 111_320 m, lon ~ 111_320 * cos(lat)
    dlat = meters / 111_320.0
    dlon = meters / (111_320.0 * max(0.1, math.cos(math.radians(at_lat))))
    return dlat, dlon


def cmd_geojson(args):
    host, port = args.host, args.port
    rate = float(args.rate)
    wait = 1.0 / rate if rate > 0 else 0

    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8"))
    coords = list(extract_coords(data))
    if not coords:
        raise SystemExit("GeoJSON sin coordenadas (LineString/MultiLineString/Points)")

    print(f"Reproduciendo {len(coords)} puntos desde {path} hacia {host}:{port} (loop={args.loop})")
    idx = 0
    while True:
        try:
            lat, lon = coords[idx]
            resp = post_pos(host, port, lat, lon, fix=args.fix, pdop=args.pdop, sats=args.sats)
            print(f"[{idx+1}/{len(coords)}] ->", lat, lon, resp.get("delivered"))
            idx += 1
            if idx >= len(coords):
                if args.loop:
                    idx = 0
                else:
                    break
            if wait: time.sleep(wait)
        except KeyboardInterrupt:
            print("bye")
            return
        except Exception as e:
            print("ERR:", e)
            time.sleep(1.0)


def extract_coords(geo):
    t = geo.get("type")
    if t == "FeatureCollection":
        for f in geo.get("features", []):
            yield from extract_coords(f)
    elif t == "Feature":
        g = geo.get("geometry") or {}
        yield from extract_coords(g)
    else:
        if t == "LineString":
            for lon, lat, *_ in geo.get("coordinates", []):
                yield lat, lon
        elif t == "MultiLineString":
            for line in geo.get("coordinates", []):
                for lon, lat, *_ in line:
                    yield lat, lon
        elif t == "Point":
            lon, lat, *_ = geo.get("coordinates", [None, None])
            if lon is not None and lat is not None:
                yield lat, lon
        # Polígonos se ignoran para recorrido


def main():
    p = argparse.ArgumentParser(description="AgroPost sender: postea posiciones a /api/pos")
    p.add_argument("--host", default="127.0.0.1", help="host del backend (IP en la LAN)")
    p.add_argument("--port", type=int, default=8000, help="puerto del backend")
    p.add_argument("--fix", type=int, default=4, help="fix_quality (opcional)")
    p.add_argument("--pdop", type=float, default=None, help="PDOP opcional")
    p.add_argument("--sats", type=int, default=None, help="satélites opcional")

    sub = p.add_subparsers(dest="cmd")

    p_health = sub.add_parser("health", help="GET /api/health")
    p_health.set_defaults(func=cmd_health)

    p_sim = sub.add_parser("simulate", help="Simulación simple")
    p_sim.add_argument("--lat", type=float, default=-34.6037)
    p_sim.add_argument("--lon", type=float, default=-58.3816)
    p_sim.add_argument("--meters", type=float, default=0.5, help="distancia entre puntos (m)")
    p_sim.add_argument("--rate", type=float, default=2.0, help="puntos por segundo")
    p_sim.set_defaults(func=cmd_simulate)

    p_gj = sub.add_parser("geojson", help="Reproducir GeoJSON")
    p_gj.add_argument("file", help="ruta a GeoJSON con LineString/Points")
    p_gj.add_argument("--rate", type=float, default=2.0, help="puntos por segundo")
    p_gj.add_argument("--loop", action="store_true")
    p_gj.set_defaults(func=cmd_geojson)

    args = p.parse_args()
    if not getattr(args, "cmd", None):
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()


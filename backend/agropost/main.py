# backend/agropost/main.py
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
from datetime import datetime, timezone
from pathlib import Path
import asyncio, math, os

app = FastAPI()

# ---- Salud y versión (YA LOS TENÉS, conserva si están) ----
START_TIME = datetime.now(timezone.utc)

@app.get("/api/health", include_in_schema=False)
def api_health():
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {"ok": True, "uptime_seconds": round(uptime, 2)}

@app.get("/api/version", include_in_schema=False)
def api_version():
    return {"version": "R1.0.0", "commit": os.environ.get("APP_COMMIT", "dev")}

# ---- WebSocket mínimo y robusto (DROP-IN) ----
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        # Punto simulado: reemplazalo por tu stream real cuando quieras
        t = 0
        base_lat, base_lon = -34.6, -58.4
        while True:
            lat = base_lat + 0.00002 * math.sin(t / 10)
            lon = base_lon + 0.00002 * math.cos(t / 10)
            msg = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "lat": lat,
                "lon": lon,
                "fix_quality": 4
            }
            await ws.send_json(msg)
            await asyncio.sleep(0.5)
            t += 1
    except WebSocketDisconnect:
        # Cliente cerró
        return
    except Exception as e:
        # Si algo falla, cerramos limpio (evita 500 en handshake siguiente)
        await ws.close(code=1011)
        print("[/ws ERROR]", repr(e))

# ---- (Opcional) logging del orden de rutas al arrancar ----
@app.on_event("startup")
async def _log_routes():
    try:
        paths = []
        for r in app.router.routes:
            path = getattr(r, "path", None)
            if path is None and hasattr(r, "routes"):
                # mounts muestran subrutas; registramos el mount
                path = getattr(r, "path_format", "MOUNT")
            paths.append(path)
        print("[ROUTES ORDER]", paths)
    except Exception as e:
        print("[ROUTES LOG ERROR]", e)

# ---- Static mount: SIEMPRE AL FINAL ----
REPO_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = (REPO_ROOT / "frontend" / "dist").resolve()

if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")
else:
    @app.get("/", include_in_schema=False)
    def _no_dist():
        return JSONResponse(
            {"error": "frontend/dist no encontrado", "esperado": str(DIST_DIR)},
            status_code=500
        )
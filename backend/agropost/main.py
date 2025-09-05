from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Set
import asyncio, os

app = FastAPI()

# ---- Salud y versión ----
START_TIME = datetime.now(timezone.utc)

@app.get("/api/health", include_in_schema=False)
def api_health():
    uptime = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {"ok": True, "uptime_seconds": round(uptime, 2)}

@app.get("/api/version", include_in_schema=False)
def api_version():
    return {"version": "R1.0.0", "commit": os.environ.get("APP_COMMIT", "dev")}


# ---- In-memory state y endpoints de datos ----
CLIENTS: Set[WebSocket] = set()
LAST_POINT: Optional[dict] = None


class Position(BaseModel):
    lat: float
    lon: float
    ts: Optional[str] = None
    fix_quality: Optional[int] = None
    pdop: Optional[float] = None
    sats: Optional[int] = None


async def _broadcast_json(data: dict) -> int:
    delivered = 0
    dead: Set[WebSocket] = set()
    for ws in list(CLIENTS):
        try:
            await ws.send_json(data)
            delivered += 1
        except Exception:
            dead.add(ws)
            try:
                await ws.close(code=1011)
            except Exception:
                pass
    for ws in dead:
        try:
            CLIENTS.remove(ws)
        except KeyError:
            pass
    return delivered


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    CLIENTS.add(ws)
    # Enviar último punto si existe
    if LAST_POINT is not None:
        try:
            await ws.send_json(LAST_POINT)
        except Exception:
            pass
    try:
        while True:
            await asyncio.sleep(3600)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("[/ws ERROR]", repr(e))
    finally:
        try:
            CLIENTS.remove(ws)
        except KeyError:
            pass


@app.post("/api/pos")
async def post_position(p: Position):
    """Recibe posición por POST y la retransmite por WS a los clientes conectados."""
    global LAST_POINT
    msg = {
        "ts": p.ts or (datetime.utcnow().isoformat() + "Z"),
        "lat": p.lat,
        "lon": p.lon,
        "fix_quality": p.fix_quality,
        "pdop": p.pdop,
        "sats": p.sats,
    }
    LAST_POINT = msg
    delivered = await _broadcast_json(msg)
    return {"ok": True, "delivered": delivered}


@app.get("/api/last")
async def get_last():
    if LAST_POINT is None:
        return JSONResponse({"ok": False, "error": "no data"}, status_code=404)
    return LAST_POINT


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


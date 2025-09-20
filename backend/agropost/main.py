from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Set
import asyncio, os, json, re
from urllib.parse import quote

app = FastAPI()

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPOS_ROOT = (REPO_ROOT / "frontend" / "public" / "campos guardados").resolve()
CAMPOS_ROOT.mkdir(parents=True, exist_ok=True)

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


# ---- Recorridos guardados por campo ----

class RecorridoCreate(BaseModel):
    nombre: str

# Helpers para gestionar archivos de recorridos por campo.
def _resolve_campo_dir(campo_id: str) -> Path:
    cid = (campo_id or '').strip()
    if not cid:
        raise HTTPException(status_code=400, detail='campo requerido')
    path = (CAMPOS_ROOT / cid).resolve()
    try:
        path.relative_to(CAMPOS_ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail='campo invalido')
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=404, detail='campo no encontrado')
    return path


def _ensure_recorridos_dir(campo_dir: Path) -> Path:
    rec_dir = (campo_dir / 'recorridos').resolve()
    try:
        rec_dir.relative_to(CAMPOS_ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail='campo invalido')
    rec_dir.mkdir(parents=True, exist_ok=True)
    return rec_dir


def _slugify_filename(nombre: str) -> str:
    base = (nombre or '').strip()
    if not base:
        raise HTTPException(status_code=400, detail='nombre requerido')
    slug = re.sub(r'[^0-9A-Za-z_-]+', '-', base)
    slug = re.sub(r'-{2,}', '-', slug).strip('-_')
    if not slug:
        raise HTTPException(status_code=400, detail='nombre invalido')
    return slug.lower()


def _recorrido_url(campo_id: str, filename: str) -> str:
    parts = [
        quote('campos guardados', safe=''),
        quote(campo_id, safe=''),
        quote('recorridos', safe=''),
        quote(filename, safe='')
    ]
    return '/' + '/'.join(parts)


def _serialize_recorrido(campo_id: str, path: Path) -> dict:
    stat = path.stat()
    return {
        'nombre': path.stem,
        'archivo': path.name,
        'url': _recorrido_url(campo_id, path.name),
        'modificado': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    }


@app.get('/api/campos/{campo_id}/recorridos')
async def listar_recorridos(campo_id: str):
    campo_dir = _resolve_campo_dir(campo_id)
    rec_dir = _ensure_recorridos_dir(campo_dir)
    recorridos = [
        _serialize_recorrido(campo_id, f)
        for f in sorted(rec_dir.glob('*.geojson'), key=lambda p: p.name.lower())
        if f.is_file()
    ]
    return {'ok': True, 'recorridos': recorridos}


@app.post('/api/campos/{campo_id}/recorridos')
async def crear_recorrido(campo_id: str, data: RecorridoCreate):
    campo_dir = _resolve_campo_dir(campo_id)
    rec_dir = _ensure_recorridos_dir(campo_dir)
    slug = _slugify_filename(data.nombre)
    filename = f"{slug}.geojson"
    filepath = (rec_dir / filename).resolve()
    try:
        filepath.relative_to(rec_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail='nombre invalido')
    if filepath.exists():
        raise HTTPException(status_code=409, detail='el recorrido ya existe')
    with filepath.open('w', encoding='utf-8') as fh:
        json.dump({'type': 'FeatureCollection', 'features': []}, fh, ensure_ascii=False)
    info = _serialize_recorrido(campo_id, filepath)
    info['nombre'] = data.nombre.strip()
    return {'ok': True, 'recorrido': info}

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


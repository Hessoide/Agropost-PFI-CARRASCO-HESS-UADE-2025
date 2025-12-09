from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Set
import asyncio, os, json, re, shutil
from urllib.parse import quote

app = FastAPI()

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPOS_ROOT = (REPO_ROOT / "frontend" / "public" / "campos guardados").resolve()
CAMPOS_ROOT.mkdir(parents=True, exist_ok=True)
INDEX_PATH = (CAMPOS_ROOT / "index.json").resolve()

app.mount("/campos guardados", StaticFiles(directory=str(CAMPOS_ROOT), html=False), name="campos-guardados")

if not INDEX_PATH.exists():
    INDEX_PATH.write_text(json.dumps({'campos': []}, ensure_ascii=False, indent=2), encoding='utf-8')


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

# ---- Helpers comunes de campos ----

def _load_campos_index():
    if not INDEX_PATH.exists():
        return []
    try:
        data = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        campos = data.get('campos')
    else:
        campos = data
    return [str(c) for c in campos] if isinstance(campos, list) else []

def _save_campos_index(campos):
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_PATH.open('w', encoding='utf-8') as fh:
        json.dump({'campos': campos}, fh, ensure_ascii=False, indent=2)

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

def _normalize_rec_filename(name: str) -> str:
    name = (name or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail='nombre requerido')
    basename = Path(name).name
    if not basename.lower().endswith('.geojson'):
        raise HTTPException(status_code=400, detail='se requiere archivo .geojson')
    stem = Path(basename).stem
    slug = _slugify_filename(stem)
    filename = f"{slug}.geojson"
    return filename


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


@app.put('/api/campos/{campo_id}/recorridos/{filename}')
async def guardar_recorrido_snapshot(campo_id: str, filename: str, request: Request):
    campo_dir = _resolve_campo_dir(campo_id)
    rec_dir = _ensure_recorridos_dir(campo_dir)
    safe_name = _normalize_rec_filename(filename)
    filepath = (rec_dir / safe_name).resolve()
    try:
        filepath.relative_to(rec_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail='nombre invalido')


    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail='payload invalido')


    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='payload invalido')


    def _as_feature(obj):
        if not isinstance(obj, dict):
            return None
        if obj.get('type') == 'Feature' and isinstance(obj.get('geometry'), dict):
            return obj
        return None


    def _apply_role(feature, role):
        if feature is None:
            return None
        props = feature.get('properties')
        if not isinstance(props, dict):
            props = {}
            feature['properties'] = props
        props['role'] = role
        return feature


    line_feature = _apply_role(_as_feature(payload.get('line')), 'line')
    coverage_feature = _apply_role(_as_feature(payload.get('coverage')), 'coverage')
    features = []
    if coverage_feature:
        features.append(coverage_feature)
    if line_feature:
        features.append(line_feature)


    if not features:
        raise HTTPException(status_code=400, detail='sin datos para guardar')


    metadata = payload.get('meta') if isinstance(payload.get('meta'), dict) else {}
    metadata = dict(metadata)
    raw_line = metadata.get('rawLine') if isinstance(metadata.get('rawLine'), list) else None
    if not raw_line:
        alt_raw = payload.get('rawLine')
        if isinstance(alt_raw, list):
            raw_line = alt_raw


    fc = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': metadata
    }
    meta_out = fc['metadata']
    meta_out['updatedAt'] = datetime.now(timezone.utc).isoformat()
    if raw_line:
        meta_out['rawLine'] = raw_line


    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'ok': True}


@app.put('/api/campos/{campo_id}/area')
async def guardar_area_snapshot(campo_id: str, request: Request):
    campo_dir = _resolve_campo_dir(campo_id)
    area_path = (campo_dir / 'area.geojson').resolve()
    try:
        area_path.relative_to(campo_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail='campo invalido')

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail='payload invalido')

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='payload invalido')

    def _as_feature(obj):
        if not isinstance(obj, dict):
            return None
        if obj.get('type') == 'Feature' and isinstance(obj.get('geometry'), dict):
            return obj
        return None

    def _apply_role(feature, role):
        if feature is None:
            return None
        props = feature.get('properties')
        if not isinstance(props, dict):
            props = {}
            feature['properties'] = props
        props['role'] = role
        return feature

    line_feature = _apply_role(_as_feature(payload.get('line')), 'line')
    coverage_feature = _apply_role(_as_feature(payload.get('coverage')), 'coverage')
    features = []
    if coverage_feature:
        features.append(coverage_feature)
    if line_feature:
        features.append(line_feature)

    if not features:
        raise HTTPException(status_code=400, detail='sin datos para guardar')

    metadata = payload.get('meta') if isinstance(payload.get('meta'), dict) else {}
    metadata = dict(metadata)
    raw_line = metadata.get('rawLine') if isinstance(metadata.get('rawLine'), list) else None
    if not raw_line:
        alt_raw = payload.get('rawLine')
        if isinstance(alt_raw, list):
            raw_line = alt_raw

    fc = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': metadata
    }
    meta_out = fc['metadata']
    meta_out['updatedAt'] = datetime.now(timezone.utc).isoformat()
    if raw_line:
        meta_out['rawLine'] = raw_line

    area_path.parent.mkdir(parents=True, exist_ok=True)
    area_path.write_text(json.dumps(fc, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'ok': True}

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

class CampoCreate(BaseModel):
    nombre: str

@app.post('/api/campos')
async def crear_campo(data: CampoCreate):
    nombre = (data.nombre or '').strip()
    if not nombre:
        raise HTTPException(status_code=400, detail='nombre requerido')

    sanitized = re.sub(r'[\\/:*?"<>|]', '-', nombre).strip()
    if not sanitized:
        raise HTTPException(status_code=400, detail='nombre invalido')

    campo_dir = (CAMPOS_ROOT / sanitized).resolve()
    try:
        campo_dir.relative_to(CAMPOS_ROOT)
    except ValueError:
        raise HTTPException(status_code=400, detail='nombre invalido')

    if campo_dir.exists():
        raise HTTPException(status_code=409, detail='el campo ya existe')

    campo_dir.mkdir(parents=True, exist_ok=False)
    (campo_dir / 'recorridos').mkdir(parents=True, exist_ok=True)

    default_area = {'type': 'FeatureCollection', 'features': []}
    default_datos = {'nombre': nombre, 'maquinaria_actual': None, 'maquinarias': []}

    (campo_dir / 'area.geojson').write_text(json.dumps(default_area, ensure_ascii=False, indent=2), encoding='utf-8')
    (campo_dir / 'datos.json').write_text(json.dumps(default_datos, ensure_ascii=False, indent=2), encoding='utf-8')

    campos = _load_campos_index()
    if sanitized not in campos:
        campos.append(sanitized)
        _save_campos_index(campos)

    return {'ok': True, 'campo': {'id': sanitized, 'nombre': nombre}}

@app.delete('/api/campos/{campo_id}')
async def borrar_campo(campo_id: str):
    campo_dir = _resolve_campo_dir(campo_id)
    shutil.rmtree(campo_dir)

    campos = [c for c in _load_campos_index() if c != campo_id]
    _save_campos_index(campos)

    return {'ok': True}

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


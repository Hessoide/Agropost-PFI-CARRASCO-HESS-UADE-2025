from pathlib import Path
import asyncio, json, math, time
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="AgroPost")

# Montar frontend compilado (frontend/dist)
FRONT_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONT_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONT_DIST), html=True), name="static")

@app.websocket("/ws")
async def ws_pos(ws: WebSocket):
    await ws.accept()
    # Simulación de puntos (círculo chiquito)
    i = 0
    while True:
        lat = -34.6 + 0.0001*math.sin(i/20)
        lon = -58.4 + 0.0001*math.cos(i/20)
        msg = {"lat": lat, "lon": lon, "fix_quality": 4}
        await ws.send_text(json.dumps(msg))
        i += 1
        await asyncio.sleep(1)

@app.get("api/health")
def health(): return {"ok": True}

# Para run local:
# uvicorn agropost.main:app --host 0.0.0.0 --port 8000

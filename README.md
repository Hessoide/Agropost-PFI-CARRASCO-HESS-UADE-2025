# AgroPost - PFI UADE 2025
Sistema de geoposicionamiento de alta precisión para agricultura de precisión en zonas sin internet.

## Integrantes
- Santiago Carrasco Vera
- Agustín Hess

## Objetivo
Desarrollar un sistema basado en GNSS y RTK que permita obtener ubicación precisa (< ±8 cm) y visualizarla en tiempo real en una interfaz táctil.

## Tecnologías
- Raspberry Pi 5
- Python
- RTKLIB / RTKLIB-Py
- LoRa
- Leaflet.js para mapas

## Como correr el proyecto:
- .\.venv\Scripts\Activate.ps1  (solo la primera vez)
- cd frontend
- npm install
- npm run build
- cd ..
- pip install -r requirements.txt
- cd backend
- uvicorn agropost.main:app --host 0.0.0.0 --port 8000

- http://localhost:8000

## Como correr el proyecto:

- 
- python .\sender\sender.py --host 192.168.56.1 --port 8000 geojson ".\frontend\public\geo\recorrido.geojson" --rate 2 --loop

192.168.56.1

- http://localhost:8000

## Modo desarrollo (hot reload)

Backend y frontend con proxies de desarrollo ya configurados en Vite:

- Terminal 1:
  - `cd backend`
  - `uvicorn agropost.main:app --host 0.0.0.0 --port 8000 --reload`
- Terminal 2:
  - `cd frontend`92.168.56.1
  - `npm run dev`
- Abrir `http://localhost:5173` (Vite proxy redirige `/api` y `/ws` al backend)

## Ejecución rápida

## API de posiciones (POST)

Envía posiciones desde tu equipo/dispositivo dentro de la red local al backend:

- URL: `POST http://<host>:8000/api/pos`
- JSON body:

```
{
  "ts": "2025-01-01T00:00:00Z",   // opcional, si falta se usa hora del servidor
  "lat": -34.6037,
  "lon": -58.3816,
  "fix_quality": 4,               // opcional (0,1,2,4,5)
  "pdop": 0.7,                    // opcional
  "sats": 18                      // opcional
}
```

Ejemplo con curl:

```
curl -X POST http://localhost:8000/api/pos \
  -H "Content-Type: application/json" \
  -d '{"lat": -34.6037, "lon": -58.3816, "fix_quality": 4, "pdop": 0.8, "sats": 17}'
```

La UI se conecta por WebSocket a `ws://<host>:8000/ws` y recibe cada punto publicado por POST.

Opción 1 (PowerShell):

```
./start.ps1
```

Opciones:
- `./start.ps1 -Reload` inicia backend con autoreload.
- `./start.ps1 -SkipFrontend` salta el build del frontend.

Opción Linux/Raspberry:

```
chmod +x ./start.sh
./start.sh              # build + backend
# variantes:
./start.sh --reload     # autoreload para desarrollo
./start.sh --skip-frontend   # salta build si ya existe frontend/dist
```

Opción 2 (CMD):

```
start.bat
```

Si PowerShell bloquea scripts:

```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./start.ps1
```

AgroPost Sender
================

CLI simple para enviar coordenadas al backend de AgroPost vía POST (`/api/pos`).
Útil para ejecutar desde otra computadora en la misma red y alimentar la UI en tiempo real.

Requisitos
- Python 3.10+

Instalación rápida (Windows/PowerShell)
```
cd sender
./start.ps1 -Host 192.168.1.10 -Port 8000 -Check
```
Esto crea un venv, instala dependencias y ejecuta un check de salud.

Uso (CLI)
```
cd sender
python sender.py --host 192.168.1.10 --port 8000 simulate --rate 2 --meters 0.5
python sender.py --host 192.168.1.10 --port 8000 geojson campo.geojson --rate 2 --loop
```

Comandos
- `simulate`: genera puntos alrededor de una ubicación (por defecto Obelisco) o la que pases con `--lat/--lon`.
  - `--meters`: distancia entre puntos consecutivos (m)
  - `--rate`: puntos por segundo
  - `--lat --lon`: centro inicial
- `geojson <file>`: recorre un GeoJSON con `LineString`, `MultiLineString` o `FeatureCollection` de Points/LineStrings. Ignora polígonos.
  - `--rate`: puntos por segundo
  - `--loop`: reitera al finalizar

Endpoint
- `POST http://<host>:<port>/api/pos` con body JSON:
```
{
  "lat": -34.6037,
  "lon": -58.3816,
  "ts": "2025-01-01T00:00:00Z",   // opcional
  "fix_quality": 4,               // opcional
  "pdop": 0.7,                    // opcional
  "sats": 18                      // opcional
}
```

Notas
- Asegúrate de que el backend esté accesible desde la red (ver firewall y que esté escuchando en 0.0.0.0).
- En la UI usa la pantalla Campo (`#/campo`).
- Si no ves el recorrido en Campo, asegurate de tener el mapa con `noTiles=true` y WS habilitado (versión actual lo permite).

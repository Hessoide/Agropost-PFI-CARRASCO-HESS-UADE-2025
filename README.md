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

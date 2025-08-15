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
- cd frontend
- npm install
- npm run build
- cd ..
- cd backend
- pip install -r requirements.txt
- uvicorn agropost.main:app --host 0.0.0.0 --port 8000

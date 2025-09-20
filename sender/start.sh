#!/usr/bin/env bash
set -euo pipefail

# Bootstrap para Linux/Raspberry: prepara venv e invoca sender.py

HOST="127.0.0.1"
PORT="8000"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PY="$VENV_DIR/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "Creando venv en $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r "$ROOT_DIR/requirements.txt"

if [[ $# -eq 0 ]]; then
  echo "Uso: ./start.sh [args de sender.py]"
  echo "Ejemplos:"
  echo "  ./start.sh --host 192.168.1.10 --port 8000 health"
  echo "  ./start.sh --host 192.168.1.10 --port 8000 simulate --rate 2 --meters 0.5"
  echo "  ./start.sh --host 192.168.1.10 --port 8000 geojson ../frontend/public/geo/recorrido.geojson --rate 2 --loop"
  exit 0
fi

exec "$PY" "$ROOT_DIR/sender.py" "$@"


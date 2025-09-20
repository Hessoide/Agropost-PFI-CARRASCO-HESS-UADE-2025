#!/usr/bin/env bash
set -euo pipefail

# AgroPost – Inicio unificado (Linux/Raspberry)

SKIP_FRONTEND=false
RELOAD=false
PORT=8000

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-frontend)
      SKIP_FRONTEND=true; shift ;;
    --reload)
      RELOAD=true; shift ;;
    -p|--port)
      PORT="${2:-}"; shift 2 ;;
    -h|--help)
      echo "Uso: $0 [--skip-frontend] [--reload] [--port N]"; exit 0 ;;
    *)
      echo "Arg desconocido: $1" >&2
      echo "Uso: $0 [--skip-frontend] [--reload] [--port N]" >&2
      exit 1 ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PY="$VENV_DIR/bin/python"

echo "AgroPost -> preparando entorno Python (venv)"
if [[ ! -x "$PY" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r "$ROOT_DIR/requirements.txt"

if [[ "$SKIP_FRONTEND" != "true" ]]; then
  echo "AgroPost -> construyendo frontend (vite)"
  if command -v npm >/dev/null 2>&1; then
    pushd "$ROOT_DIR/frontend" >/dev/null
    if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
    npm run build
    popd >/dev/null
  else
    echo "npm no encontrado; saltando build del frontend. Use --skip-frontend o instale Node.js." >&2
  fi
fi

echo "AgroPost -> levantando backend en http://0.0.0.0:$PORT"
cd "$ROOT_DIR/backend"
ARGS=( "agropost.main:app" "--host" "0.0.0.0" "--port" "$PORT" )
if [[ "$RELOAD" == "true" ]]; then ARGS+=( "--reload" ); fi
exec "$PY" -m uvicorn "${ARGS[@]}"


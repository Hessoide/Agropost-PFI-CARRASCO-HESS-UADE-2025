param(
  [string]$ApiHost = "127.0.0.1",
  [int]$Port = 8000,
  [switch]$Check
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root ".venv"
$py = Join-Path $venv "Scripts/python.exe"

if (-not (Test-Path $py)) {
  Write-Host "Creando venv en $venv"
  & py -3 -m venv $venv
}

& $py -m pip install --upgrade pip > $null
& $py -m pip install -r (Join-Path $root 'requirements.txt')

if ($Check) {
  & $py (Join-Path $root 'sender.py') health --host $ApiHost --port $Port
} else {
  Write-Host "Ejemplos:" -ForegroundColor Cyan
  Write-Host "  python sender.py --host $ApiHost --port $Port simulate --rate 2" -ForegroundColor DarkGray
  Write-Host "  python sender.py --host $ApiHost --port $Port geojson ..\frontend\public\geo\recorrido.geojson --rate 2" -ForegroundColor DarkGray
}


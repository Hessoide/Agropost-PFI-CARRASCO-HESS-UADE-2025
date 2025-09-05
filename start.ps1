param(
  [switch]$SkipFrontend = $false,
  [switch]$Reload = $false,
  [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Write-Host "AgroPost • Inicio unificado" -ForegroundColor Cyan

# --- Python/venv ---
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) { $pythonCmd = "py -3" } else {
  $pythonExe = Get-Command python -ErrorAction SilentlyContinue
  if (-not $pythonExe) { Write-Error "Python 3 no encontrado. Instálalo y reintenta."; exit 1 }
  $pythonCmd = "python"
}

$venvPath = Join-Path $root ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
  Write-Host "Creando entorno virtual en $venvPath"
  & $pythonCmd -m venv $venvPath
}

Write-Host "Instalando dependencias de backend (pip)"
& $venvPython -m pip install --upgrade pip > $null
& $venvPython -m pip install -r (Join-Path $root "requirements.txt")

# --- Frontend build ---
if (-not $SkipFrontend) {
  $fePath = Join-Path $root "frontend"
  if (-not (Test-Path $fePath)) { Write-Error "No se encontró la carpeta 'frontend'"; exit 1 }
  $npm = Get-Command npm -ErrorAction SilentlyContinue
  if (-not $npm) { Write-Error "npm no encontrado. Instala Node.js LTS"; exit 1 }

  Push-Location $fePath
  try {
    if (Test-Path "package-lock.json") { npm ci } else { npm install }
    npm run build
  }
  finally { Pop-Location }
}

# --- Backend run ---
$backendPath = Join-Path $root "backend"
if (-not (Test-Path $backendPath)) { Write-Error "No se encontró la carpeta 'backend'"; exit 1 }

$args = @("agropost.main:app", "--host", "0.0.0.0", "--port", $Port.ToString())
if ($Reload) { $args += "--reload" }

Write-Host "Levantando backend en http://localhost:$Port" -ForegroundColor Green
Push-Location $backendPath
try {
  & $venvPython -m uvicorn @args
}
finally { Pop-Location }


# Abre el sitio AguaAlerta (web + API) en http://localhost:8000
# Uso:  .\scripts\run-web.ps1              (prepara todo lo que falte y abre el sitio)
#       .\scripts\run-web.ps1 -NoStart     (solo prepara: entorno de Python, dependencias y compilación de la web)
#       .\scripts\run-web.ps1 -Rebuild     (vuelve a compilar la web aunque ya exista)
# Requiere Python 3.12 o posterior y Node.js 20 o posterior. Funciona sin Telegram: el newsletter se activa al poner el
# token del bot en .env (ver .env.example y docs/predicciones.md).
param([switch]$NoStart, [switch]$Rebuild, [int]$Port = 8000)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

# --- Python: entorno virtual y dependencias ---
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Instala Python 3.12 o posterior y agrega python al PATH." }
    Write-Host "Creando entorno virtual..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual .venv." }
}
& $py -c "import sys; sys.exit(sys.version_info < (3, 12))"
if ($LASTEXITCODE -ne 0) { throw "Usa Python 3.12 o posterior para crear .venv." }
$checkImports = @'
try:
    import fastapi, uvicorn, pandas, statsmodels, pyarrow, openpyxl, requests
except ImportError:
    raise SystemExit(1)
'@
& $py -c $checkImports
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando dependencias de Python..."
    & $py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias. Revisa la salida de pip." }
}

# --- Web: dependencias y compilación (la API sirve web\dist) ---
$web = Join-Path $root "web"
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "Instala Node.js 20 o posterior (incluye npm)." }
if (-not (Test-Path (Join-Path $web "node_modules"))) {
    Write-Host "Instalando dependencias de la web..."
    Push-Location $web
    npm.cmd ci
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { throw "npm ci falló. Revisa la salida." }
}
if ($Rebuild -or -not (Test-Path (Join-Path $web "dist\index.html"))) {
    Write-Host "Compilando la web..."
    Push-Location $web
    npm.cmd run build
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { throw "La compilación de la web falló." }
}

if ($NoStart) { Write-Host "Todo listo. Para abrir el sitio: .\scripts\run-web.ps1"; return }
if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Host "Aviso: no hay .env, así que el newsletter de Telegram queda apagado (copia .env.example como .env y pon el token del bot)."
}
Write-Host "AguaAlerta en http://localhost:$Port  (Ctrl+C para detener)"
& $py -m uvicorn src.web_api:app --host 127.0.0.1 --port $Port

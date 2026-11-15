# Abre Hefesto (Detective Tico) en http://localhost:8501
# Uso:  .\scripts\run.ps1         (crea .venv e instala dependencias solo si hace falta)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Instala Python 3.12 o posterior y agrega python al PATH."
    }
    Write-Host "Creando entorno virtual..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual .venv." }
}
& $py -c "import sys; sys.exit(sys.version_info < (3, 12))"
if ($LASTEXITCODE -ne 0) { throw "Usa Python 3.12 o posterior para crear .venv." }

# Windows PowerShell convierte stderr redirigido de un programa nativo en errores.
$checkImports = @'
try:
    import streamlit, pandas, plotly, statsmodels, pyarrow
except ImportError:
    raise SystemExit(1)
'@
& $py -c $checkImports
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando dependencias..."
    & $py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudieron instalar las dependencias. Revisa la salida de pip."
    }
}
& $py scripts\verify_data.py
if ($LASTEXITCODE -ne 0) { throw "La verificación de datos falló." }
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
& $py -m streamlit run app.py --server.port 8501

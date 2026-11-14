# Abre Hefesto (Detective Tico) en http://localhost:8501
# Uso:  .\run.ps1          (crea .venv e instala dependencias solo si hace falta)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creando entorno virtual..."
    python -m venv .venv
    & $py -m pip install -r requirements.txt
}
& $py -c "import streamlit, pandas, plotly, statsmodels, pyarrow" 2>$null
if ($LASTEXITCODE -ne 0) { & $py -m pip install -r requirements.txt }
& $py scripts\verify_data.py
if ($LASTEXITCODE -ne 0) { throw "La verificación de datos falló." }
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
& $py -m streamlit run app.py --server.port 8501

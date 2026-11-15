# Crea dist\hefesto-mvp.zip con lo necesario para correr el producto (sin .venv ni módulos fuera de alcance).
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$out = Join-Path $root "dist"
$stage = Join-Path $out "hefesto-mvp"
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Path $stage | Out-Null
$items = "app.py","requirements.txt","README.md","LICENSE","THIRD_PARTY.md",".streamlit","config","src","scripts","docs"
foreach ($i in $items) { Copy-Item $i -Destination $stage -Recurse }
New-Item -ItemType Directory -Path "$stage\data" | Out-Null
Copy-Item "data\processed" "$stage\data\processed" -Recurse
Copy-Item "data\raw" "$stage\data\raw" -Recurse
Copy-Item "data\web" "$stage\data\web" -Recurse
# Fuera de alcance del MVP (agua/AyA/pronóstico/cantones): no se empaquetan.
Remove-Item "$stage\data\processed\water_*.csv" -ErrorAction SilentlyContinue
Remove-Item "$stage\data\web\local.json","$stage\data\web\cantons.json" -ErrorAction SilentlyContinue
Get-ChildItem $stage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Compress-Archive -Path $stage -DestinationPath "$out\hefesto-mvp.zip"
(Get-FileHash "$out\hefesto-mvp.zip" -Algorithm SHA256).Hash | Set-Content "$out\hefesto-mvp.zip.sha256"
Write-Host "Listo: $out\hefesto-mvp.zip"

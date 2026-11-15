# Envío diario del newsletter de Telegram de AguaAlerta. Lo ejecuta el Programador de tareas de Windows (tarea «AguaAlerta-Telegram»).
# Las suscripciones nuevas se activan solas mientras la API está corriendo (revisa los /start cada pocos segundos);
# esto envía las alertas y el resumen diario a quienes ya están activos. Deja un registro en data\newsletter.log.
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$log = Join-Path $root "data\newsletter.log"
"[$(Get-Date -Format 's')] envío diario" | Out-File -FilePath $log -Append -Encoding utf8
$env:PYTHONIOENCODING = "utf-8"
& $python -m src.telegram_newsletter send --yes 2>&1 | Out-File -FilePath $log -Append -Encoding utf8

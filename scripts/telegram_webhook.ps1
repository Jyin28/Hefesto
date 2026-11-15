# Conecta (o desconecta) el bot de Telegram con el sitio publicado en Vercel.
#
# En Vercel no hay un proceso que revise los mensajes del bot: Telegram los entrega al sitio (/api/telegram). Hay que decirle
# a Telegram esa dirección una vez, después del primer deploy (y de nuevo si cambia el dominio o el secreto).
#
# Uso:  .\scripts\telegram_webhook.ps1 -Url https://tu-sitio.vercel.app    (conecta el bot con Vercel)
#       .\scripts\telegram_webhook.ps1 -Estado                             (muestra a dónde entrega Telegram ahora)
#       .\scripts\telegram_webhook.ps1 -Quitar                             (desconecta: vuelve el modo local con la API del puerto 8000)
#
# Lee TELEGRAM_BOT_TOKEN y TELEGRAM_WEBHOOK_SECRET del archivo .env de la raíz (o de variables de entorno). El secreto debe ser
# el MISMO que pusiste en las variables de entorno de Vercel. Nunca se muestra el token.
param([string]$Url, [switch]$Quitar, [switch]$Estado)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

function Get-Setting([string]$name) {
    $fromEnv = [Environment]::GetEnvironmentVariable($name)
    if ($fromEnv) { return $fromEnv.Trim() }
    $dotenv = Join-Path $root ".env"
    if (Test-Path $dotenv) {
        foreach ($line in Get-Content $dotenv -Encoding UTF8) {
            $key, $value = $line -split "=", 2
            if ($key.Trim() -eq $name -and $value) { return $value.Trim().Trim("'", '"') }
        }
    }
    return $null
}

$token = Get-Setting "TELEGRAM_BOT_TOKEN"
if (-not $token) { throw "Falta TELEGRAM_BOT_TOKEN en .env (o como variable de entorno)." }

function Invoke-Telegram([string]$method, [hashtable]$body = @{}) {
    try {
        $reply = Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$token/$method" -ContentType "application/json" -Body ($body | ConvertTo-Json)
    } catch {
        throw "Telegram rechazó $method. Revisa el token y la conexión."  # el mensaje original lleva la dirección con el token
    }
    if (-not $reply.ok) { throw "Telegram rechazó ${method}: $($reply.description)" }
    return $reply.result
}

if ($Quitar) {
    Invoke-Telegram "deleteWebhook" @{ drop_pending_updates = $false } | Out-Null
    Write-Host "Listo: el bot ya no entrega a Vercel. En local, la API del puerto 8000 vuelve a revisar los /start."
    return
}
if ($Estado -or -not $Url) {
    $info = Invoke-Telegram "getWebhookInfo"
    if ($info.url) { Write-Host "Telegram entrega a: $($info.url)  (pendientes: $($info.pending_update_count))" } else { Write-Host "Sin webhook: el bot no entrega a ningún sitio (modo local)." }
    if ($info.last_error_message) { Write-Host "Último error de Telegram: $($info.last_error_message)" }
    if (-not $Url) { return }
}

$secret = Get-Setting "TELEGRAM_WEBHOOK_SECRET"
if (-not $secret) { throw "Falta TELEGRAM_WEBHOOK_SECRET (texto al azar; el mismo que en Vercel). Solo letras, números, _ y -; hasta 256 caracteres." }
if ($secret -notmatch '^[A-Za-z0-9_-]{1,256}$') { throw "TELEGRAM_WEBHOOK_SECRET solo puede llevar letras, números, _ y - (hasta 256 caracteres)." }
if ($Url -notmatch '^https://[^/\s]+') { throw "-Url debe ser la dirección https del sitio, por ejemplo https://tu-sitio.vercel.app" }
$hook = $Url.TrimEnd("/") + "/api/telegram"
Invoke-Telegram "setWebhook" @{ url = $hook; secret_token = $secret; allowed_updates = @("message"); drop_pending_updates = $false } | Out-Null
Write-Host "Listo: Telegram entregará los mensajes del bot a $hook"
Write-Host "Importante: mientras el webhook esté activo, la API local (puerto 8000) no puede leer los /start. Para volver a local: .\scripts\telegram_webhook.ps1 -Quitar"

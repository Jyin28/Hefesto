#!/usr/bin/env bash
# Mata cualquier servidor Vite previo de este proyecto y lo vuelve a levantar
# con el código más reciente (sin caché de Vite, sin procesos huérfanos).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "== Buscando procesos previos en los puertos 5173-5180 =="
for port in $(seq 5173 5180); do
  pids=$(netstat -ano 2>/dev/null | grep "LISTENING" | grep ":$port " | awk '{print $NF}' | sort -u)
  for pid in $pids; do
    if [ -n "$pid" ] && [ "$pid" != "0" ]; then
      echo "  Matando PID $pid (puerto $port)"
      taskkill //F //PID "$pid" >/dev/null 2>&1 || true
    fi
  done
done

echo "== Buscando procesos node/vite huérfanos de este proyecto =="
wmic process where "CommandLine like '%web%vite%'" get ProcessId 2>/dev/null \
  | tr -d '\r' | grep -E '^[0-9]+$' | while read -r pid; do
      echo "  Matando PID huérfano $pid"
      taskkill //F //PID "$pid" >/dev/null 2>&1 || true
    done

echo "== Limpiando caché de Vite para forzar el código más reciente =="
rm -rf "$WEB_DIR/node_modules/.vite"

sleep 1

echo "== Levantando el servidor de desarrollo =="
cd "$WEB_DIR"
LOG_FILE="$(mktemp)"
npm run dev > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

URL=""
for _ in $(seq 1 40); do
  CLEAN="$(sed -E 's/\x1b\[[0-9;]*m//g' "$LOG_FILE" 2>/dev/null)"
  if echo "$CLEAN" | grep -q "Local:"; then
    URL=$(echo "$CLEAN" | grep -m1 "Local:" | grep -oE 'http://[^ ]+')
    break
  fi
  sleep 0.5
done

if [ -z "$URL" ]; then
  echo "No se detectó la URL del servidor. Revisa el log: $LOG_FILE"
  exit 1
fi

echo "Servidor corriendo (PID $SERVER_PID) en $URL"
echo "Log: $LOG_FILE"

cmd.exe //c start "" "$URL" >/dev/null 2>&1 || true

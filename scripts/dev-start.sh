#!/bin/bash
set -e

WORKSPACE="/workspaces/Szczypior-Discord-Bot"
LOG_DIR="/tmp/dev-logs"
NPM=$(which npm 2>/dev/null || echo "npm")
mkdir -p "$LOG_DIR"

echo "[dev-start] Uruchamiam środowisko deweloperskie..."

# --- Node dependencies ---
if [ ! -d "$WORKSPACE/services/web-dashboard/temp-react/node_modules" ]; then
  echo "[dev-start] Kopiuję node_modules z obrazu..."
  cp -r /tmp/react-install/node_modules "$WORKSPACE/services/web-dashboard/temp-react/node_modules"
fi

# --- Vite (React) ---
echo "[dev-start] Startuję Vite dev server (port 8080)..."
cd "$WORKSPACE/services/web-dashboard/temp-react"
nohup "$NPM" run dev > "$LOG_DIR/vite.log" 2>&1 &
echo $! > "$LOG_DIR/vite.pid"

# --- Django ---
echo "[dev-start] Startuję Django dev server (port 8000)..."
cd "$WORKSPACE/services/web-dashboard"
nohup python manage.py runserver 0.0.0.0:8000 > "$LOG_DIR/django.log" 2>&1 &
echo $! > "$LOG_DIR/django.pid"

echo "[dev-start] Gotowe!"
echo "  Django  → http://localhost:8000  (logi: $LOG_DIR/django.log)"
echo "  Vite    → http://localhost:8080  (logi: $LOG_DIR/vite.log)"

#!/bin/sh
set -eu

cd /workspaces/Szczypior-Discord-Bot

echo "[postCreate] Python dependencies installed at build time."

echo "[postCreate] Instaluję zależności npm (React/Vite)..."
cd services/web-dashboard/react && npm install

cd /workspaces/Szczypior-Discord-Bot
chmod +x scripts/dev-start.sh

echo "[postCreate] Setup zakończony."

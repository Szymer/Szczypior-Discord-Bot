#!/bin/bash
# Lokalne testowanie deploymentu Web Dashboard

set -e

echo "🧪 Testowanie Web Dashboard Dockerfile lokalnie..."

# Build obrazu
echo "📦 Budowanie obrazu..."
cd /workspaces/Szczypior-Discord-Bot
docker build -f infrastructure/docker/web-dashboard.Dockerfile -t szczypior-web-dashboard:test .

echo "✅ Obraz zbudowany pomyślnie!"
echo ""
echo "Aby uruchomić lokalnie:"
echo "docker run -p 8000:8000 \\"
echo "  -e DJANGO_SECRET_KEY='test-secret-key' \\"
echo "  -e DEBUG=True \\"
echo "  -e DB_NAME=postgres \\"
echo "  -e DB_USER=postgres.wpvjryhrhigqqccblkav \\"
echo "  -e DB_PASSWORD='DziwnaDupaAgnieszki3456!!!' \\"
echo "  -e DB_HOST=aws-1-eu-north-1.pooler.supabase.com \\"
echo "  -e DB_PORT=6543 \\"
echo "  szczypior-web-dashboard:test"

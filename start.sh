#!/bin/bash
# Inicia NFeHub API + Frontend
# Uso: ./start.sh [dev|prod]

set -e
cd "$(dirname "$0")"

MODE="${1:-prod}"

if [ "$MODE" = "dev" ]; then
    echo "=== Modo DEV ==="
    echo "Iniciando API em http://localhost:8000"
    echo "Iniciando Frontend em http://localhost:5173"
    echo ""
    # API em background
    python3 -m api.main &
    API_PID=$!
    # Frontend dev server
    cd app && npx vite --host &
    FRONT_PID=$!
    trap "kill $API_PID $FRONT_PID 2>/dev/null" EXIT
    wait
else
    echo "=== Modo PROD ==="
    echo "Frontend servido pelo FastAPI em http://localhost:8000"
    echo ""
    # Build frontend se necessario
    if [ ! -d "app/dist" ]; then
        echo "Build do frontend..."
        cd app && npm run build && cd ..
    fi
    python3 -m api.main
fi

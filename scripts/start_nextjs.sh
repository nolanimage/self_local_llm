#!/bin/bash
# Start Next.js web interface and API server

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Starting Next.js Web Interface"
echo "=========================================="
echo ""

# Check if API server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Starting API server..."
    cd "$PROJECT_DIR"
    
    if [ ! -f "api_server.py" ]; then
        echo "❌ Error: api_server.py not found in $PROJECT_DIR"
        exit 1
    fi
    
    python3 api_server.py > api_server.log 2>&1 &
    API_PID=$!
    echo "API server started (PID: $API_PID)"
    echo "Logs: $PROJECT_DIR/api_server.log"
    sleep 3
else
    echo "✓ API server already running"
fi

# Start Next.js dev server
echo ""
echo "Starting Next.js development server..."
cd "$PROJECT_DIR/web"

if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found in $PROJECT_DIR/web"
    echo "Please run: cd web && npm install"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules not found. Installing dependencies..."
    npm install
fi

npm run dev

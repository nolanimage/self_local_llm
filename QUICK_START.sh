#!/bin/bash
# Quick Start Script for Self LLM
# This script helps you get started quickly

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    Self LLM Quick Start                          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi
echo "  ✓ Docker found"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
echo "  ✓ Docker Compose found"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+ first."
    exit 1
fi
echo "  ✓ Python 3 found"

# Check Node.js (optional, for web interface)
if ! command -v node &> /dev/null; then
    echo "  ⚠️  Node.js not found (optional, for web interface)"
else
    echo "  ✓ Node.js found"
fi

echo ""
echo "🔧 Configuration check..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "  ⚠️  .env file not found"
    echo "  Creating .env from config.env.example..."
    cp config.env.example .env
    echo "  ✓ .env created"
    echo ""
    echo "  ⚠️  IMPORTANT: Please edit .env and set RABBITMQ_PASS to a secure password!"
    echo "  Press Enter to continue after editing .env (or Ctrl+C to exit)..."
    read -r
else
    echo "  ✓ .env file found"
fi

echo ""
echo "🚀 Starting services..."

# Step 1: Start Docker services
echo ""
echo "Step 1: Starting Docker services (RabbitMQ, Ollama)..."
if docker-compose -f docker-compose.rag.yml ps | grep -q "rabbitmq.*Up"; then
    echo "  ✓ RabbitMQ already running"
else
    docker-compose -f docker-compose.rag.yml up -d rabbitmq ollama
    echo "  ✓ RabbitMQ and Ollama started"
    echo "  ⏳ Waiting for services to be ready..."
    sleep 10
fi

# Step 2: Pull Ollama model (if needed)
echo ""
echo "Step 2: Checking Ollama model..."
if docker exec ollama_server ollama list | grep -q "qwen2.5:1.5b"; then
    echo "  ✓ Ollama model already installed"
else
    echo "  📥 Pulling Ollama model (this may take a few minutes)..."
    docker exec ollama_server ollama pull qwen2.5:1.5b
    echo "  ✓ Ollama model installed"
fi

# Step 3: Start worker and updater
echo ""
echo "Step 3: Starting RAG worker and RSS updater..."
docker-compose -f docker-compose.rag.yml up -d worker rag_updater
echo "  ✓ Worker and updater started"
sleep 5

# Step 4: Check API server
echo ""
echo "Step 4: Checking API server..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✓ API server already running"
else
    echo "  🚀 Starting API server..."
    python3 api_server.py > api_server.log 2>&1 &
    API_PID=$!
    echo "  ✓ API server started (PID: $API_PID, logs: api_server.log)"
    sleep 3
fi

# Step 5: Check web interface
echo ""
echo "Step 5: Web interface setup..."
if [ -d "web" ] && [ -f "web/package.json" ]; then
    if [ ! -d "web/node_modules" ]; then
        echo "  📦 Installing web dependencies..."
        cd web
        npm install
        cd ..
        echo "  ✓ Web dependencies installed"
    else
        echo "  ✓ Web dependencies already installed"
    fi
else
    echo "  ⚠️  Web directory not found, skipping web interface"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete! 🎉                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ All services are running!"
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.rag.yml ps
echo ""
echo "🌐 Access Points:"
echo "  - Next.js Web Interface: http://localhost:3000"
echo "  - Streamlit Web Interface: http://localhost:8501 (run: streamlit run web_interface.py)"
echo "  - API Server: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - RabbitMQ Management: http://localhost:15672 (admin/admin123)"
echo ""
echo "📝 Next Steps:"
echo "  1. Start Next.js web interface:"
echo "     cd web && npm run dev"
echo ""
echo "  2. Or use the startup script:"
echo "     ./scripts/start_nextjs.sh"
echo ""
echo "  3. Test the system:"
echo "     python3 tests/test_quality_improvements.py"
echo ""
echo "📚 Documentation:"
echo "  - Installation Guide: INSTALLATION.md"
echo "  - Main README: README.md"
echo "  - Security Guide: docs/SECURITY.md"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose -f docker-compose.rag.yml down"
echo "   pkill -f api_server.py"
echo ""

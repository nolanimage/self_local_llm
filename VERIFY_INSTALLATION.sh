#!/bin/bash
# Verification script to test the entire pipeline

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              Self LLM Installation Verification                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

PASSED=0
FAILED=0

# Function to test and report
test_check() {
    local name="$1"
    local command="$2"
    
    echo -n "Testing: $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo "✅ PASS"
        ((PASSED++))
        return 0
    else
        echo "❌ FAIL"
        ((FAILED++))
        return 1
    fi
}

# 1. Check Docker services
echo "📦 Docker Services:"
test_check "RabbitMQ is running" "docker ps | grep -q rabbitmq"
test_check "Ollama is running" "docker ps | grep -q ollama_server"
test_check "Worker is running" "docker ps | grep -q llm_worker_rag"
test_check "RSS Updater is running" "docker ps | grep -q rag_updater"

# 2. Check ports
echo ""
echo "🔌 Network Ports:"
test_check "RabbitMQ port 5672" "nc -z localhost 5672"
test_check "RabbitMQ management 15672" "nc -z localhost 15672"
test_check "Ollama port 11434" "nc -z localhost 11434"
test_check "API server port 8000" "nc -z localhost 8000"

# 3. Check API endpoints
echo ""
echo "🌐 API Endpoints:"
test_check "API health endpoint" "curl -s http://localhost:8000/health | grep -q 'ok'"
test_check "API RAG stats endpoint" "curl -s http://localhost:8000/api/rag/stats > /dev/null"

# 4. Check RabbitMQ connection
echo ""
echo "🐰 RabbitMQ:"
test_check "RabbitMQ management UI" "curl -s -u admin:admin123 http://localhost:15672/api/overview > /dev/null"

# 5. Check Ollama
echo ""
echo "🤖 Ollama:"
test_check "Ollama API" "curl -s http://localhost:11434/api/tags > /dev/null"
test_check "Ollama model installed" "docker exec ollama_server ollama list | grep -q qwen2.5:1.5b"

# 6. Check Python dependencies
echo ""
echo "🐍 Python:"
test_check "Python 3 installed" "python3 --version"
test_check "Required packages" "python3 -c 'import pika, fastapi, requests' 2>/dev/null"

# 7. Check Node.js (optional)
echo ""
echo "📦 Node.js (optional):"
if command -v node &> /dev/null; then
    test_check "Node.js installed" "node --version"
    if [ -d "web" ] && [ -d "web/node_modules" ]; then
        test_check "Web dependencies installed" "test -d web/node_modules"
    else
        echo "  ⚠️  Web dependencies not installed (run: cd web && npm install)"
    fi
else
    echo "  ⚠️  Node.js not installed (optional for web interface)"
fi

# 8. Check files
echo ""
echo "📁 Files:"
test_check ".env file exists" "test -f .env"
test_check "docker-compose.rag.yml exists" "test -f docker-compose.rag.yml"
test_check "api_server.py exists" "test -f api_server.py"
test_check "app/worker_rag.py exists" "test -f app/worker_rag.py"

# Summary
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                      Verification Summary                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 All checks passed! Your installation is working correctly."
    echo ""
    echo "Next steps:"
    echo "  1. Start web interface: cd web && npm run dev"
    echo "  2. Test the system: python3 tests/test_quality_improvements.py"
    exit 0
else
    echo "⚠️  Some checks failed. Please review the errors above."
    echo ""
    echo "Common fixes:"
    echo "  - Start Docker services: docker-compose -f docker-compose.rag.yml up -d"
    echo "  - Start API server: python3 api_server.py"
    echo "  - Check logs: docker-compose -f docker-compose.rag.yml logs"
    exit 1
fi

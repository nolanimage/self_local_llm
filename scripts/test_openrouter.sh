#!/bin/bash
# Test script to compare Ollama vs OpenRouter speed

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         Speed Test: Ollama vs OpenRouter                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

if [ -z "$1" ]; then
    echo "❌ Usage: ./test_openrouter.sh YOUR_OPENROUTER_API_KEY"
    echo ""
    echo "This script will:"
    echo "  1. Test current backend (Ollama)"
    echo "  2. Switch to OpenRouter"
    echo "  3. Test OpenRouter"
    echo "  4. Show speed comparison"
    echo ""
    echo "Get a free API key at: https://openrouter.ai/"
    exit 1
fi

API_KEY=$1

echo "📊 Test 1: Current Backend (Ollama)"
echo "───────────────────────────────────────"
START=$(date +%s)
docker exec llm_worker_rag python3 -c "
from app.worker_ollama import LLMWorker
worker = LLMWorker()
result = worker.call_ollama('你好，今天天氣如何？', max_tokens=50)
print(f'Response: {result[:100]}...')
" 2>&1 | grep -v "WARNING\|FutureWarning"
END=$(date +%s)
OLLAMA_TIME=$((END - START))
echo "Time: ${OLLAMA_TIME}s"
echo ""

echo "🔄 Switching to OpenRouter..."
docker exec -e USE_OPENROUTER=true -e OPENROUTER_API_KEY=$API_KEY llm_worker_rag sh -c "
export USE_OPENROUTER=true
export OPENROUTER_API_KEY=$API_KEY
python3 -c '
from app.worker_ollama import LLMWorker
worker = LLMWorker()
print(f\"Backend: {\"OpenRouter\" if worker.use_openrouter else \"Ollama\"}\")
'
" 2>&1 | grep "Backend"
echo ""

echo "📊 Test 2: OpenRouter Backend"
echo "───────────────────────────────────────"
START=$(date +%s)
docker exec -e USE_OPENROUTER=true -e OPENROUTER_API_KEY=$API_KEY llm_worker_rag sh -c "
export USE_OPENROUTER=true
export OPENROUTER_API_KEY=$API_KEY
python3 -c \"
from app.worker_ollama import LLMWorker
worker = LLMWorker()
result = worker.call_openrouter('你好，今天天氣如何？', max_tokens=50)
print(f'Response: {result[:100]}...')
\"
" 2>&1 | grep -v "WARNING\|FutureWarning"
END=$(date +%s)
OPENROUTER_TIME=$((END - START))
echo "Time: ${OPENROUTER_TIME}s"
echo ""

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    Performance Comparison                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Ollama:      ${OLLAMA_TIME}s"
echo "  OpenRouter:  ${OPENROUTER_TIME}s"
echo ""

if [ $OPENROUTER_TIME -lt $OLLAMA_TIME ]; then
    SPEEDUP=$((OLLAMA_TIME / OPENROUTER_TIME))
    echo "  ⚡ OpenRouter is ${SPEEDUP}x faster!"
else
    echo "  Ollama performed better this time"
fi
echo ""

echo "To enable OpenRouter permanently, edit docker-compose.rag.yml:"
echo "  USE_OPENROUTER: \"true\""
echo "  OPENROUTER_API_KEY: \"$API_KEY\""
echo ""
echo "Then restart: docker-compose -f docker-compose.rag.yml restart worker"

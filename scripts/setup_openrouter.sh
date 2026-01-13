#!/bin/bash
# Interactive setup script for OpenRouter API

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

clear
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         OpenRouter Setup - Interactive Configuration            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if API key is provided as argument
if [ -n "$1" ]; then
    API_KEY="$1"
    echo "✓ Using API key from command line"
else
    # Interactive mode
    echo "Step 1: Get your FREE OpenRouter API Key"
    echo "────────────────────────────────────────────"
    echo "1. Visit: https://openrouter.ai/"
    echo "2. Click 'Sign Up' (free, no credit card needed)"
    echo "3. Go to Settings → API Keys"
    echo "4. Click 'Create Key' and copy it"
    echo ""
    echo "Press Enter when you have your API key ready..."
    read -r
    
    echo ""
    echo "Step 2: Enter Your API Key"
    echo "────────────────────────────────────────────"
    echo "Paste your API key here (it will be hidden):"
    read -rs API_KEY
    echo ""
fi

# Validate API key format
if [[ ! $API_KEY =~ ^sk-or-v1- ]]; then
    echo "❌ Error: Invalid API key format"
    echo "   API keys should start with 'sk-or-v1-'"
    echo ""
    echo "   Please get a valid key from: https://openrouter.ai/"
    exit 1
fi

echo "✓ API key validated: ${API_KEY:0:15}..."
echo ""

# Choose model
echo "Step 3: Choose Your Model"
echo "────────────────────────────────────────────"
echo "1. moonshotai/kimi-k2:free (Recommended for Chinese) ⭐"
echo "2. qwen/qwen-2-7b-instruct:free (Good for Chinese + English)"
echo "3. google/gemma-2-9b-it:free (Excellent quality)"
echo "4. meta-llama/llama-3-8b-instruct:free (Fast)"
echo ""
echo "Enter your choice [1-4] (default: 1):"
read -r choice

case $choice in
    2) MODEL="qwen/qwen-2-7b-instruct:free" ;;
    3) MODEL="google/gemma-2-9b-it:free" ;;
    4) MODEL="meta-llama/llama-3-8b-instruct:free" ;;
    *) MODEL="moonshotai/kimi-k2:free" ;;
esac

echo "✓ Selected model: $MODEL"
echo ""

# Update docker-compose.rag.yml
echo "Step 4: Updating Configuration"
echo "────────────────────────────────────────────"

# Backup
cp docker-compose.rag.yml docker-compose.rag.yml.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backup created"

# Update using sed (works on both macOS and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|USE_OPENROUTER:\${USE_OPENROUTER:-.*}|USE_OPENROUTER:\${USE_OPENROUTER:-true}|" docker-compose.rag.yml
    sed -i '' "s|OPENROUTER_API_KEY:\${OPENROUTER_API_KEY:-.*}|OPENROUTER_API_KEY:\${OPENROUTER_API_KEY:-$API_KEY}|" docker-compose.rag.yml
    sed -i '' "s|OPENROUTER_MODEL:\${OPENROUTER_MODEL:-.*}|OPENROUTER_MODEL:\${OPENROUTER_MODEL:-$MODEL}|" docker-compose.rag.yml
else
    # Linux
    sed -i "s|USE_OPENROUTER:\${USE_OPENROUTER:-.*}|USE_OPENROUTER:\${USE_OPENROUTER:-true}|" docker-compose.rag.yml
    sed -i "s|OPENROUTER_API_KEY:\${OPENROUTER_API_KEY:-.*}|OPENROUTER_API_KEY:\${OPENROUTER_API_KEY:-$API_KEY}|" docker-compose.rag.yml
    sed -i "s|OPENROUTER_MODEL:\${OPENROUTER_MODEL:-.*}|OPENROUTER_MODEL:\${OPENROUTER_MODEL:-$MODEL}|" docker-compose.rag.yml
fi

echo "✓ Configuration updated"
echo ""

# Restart services
echo "Step 5: Restarting Services"
echo "────────────────────────────────────────────"
echo "Restarting worker with OpenRouter..."

docker-compose -f docker-compose.rag.yml restart worker

echo "✓ Worker restarted"
echo ""

# Wait for startup
echo "Waiting for worker to initialize..."
sleep 5
echo ""

# Verify
echo "Step 6: Verification"
echo "────────────────────────────────────────────"

if docker logs llm_worker_rag 2>&1 | tail -20 | grep -q "OpenRouter mode enabled"; then
    echo "✅ SUCCESS! OpenRouter is now active!"
    echo ""
    echo "Backend: OpenRouter"
    echo "Model: $MODEL"
    echo "Status: Running"
else
    echo "⚠️  Worker started but verification unclear"
    echo "   Check logs: docker logs llm_worker_rag"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete! 🎉                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next Steps:"
echo "1. Test your setup at: http://localhost:3000"
echo "2. Try asking: '今天香港新聞'"
echo "3. You should see 3-5x faster responses!"
echo ""
echo "To switch back to Ollama later:"
echo "  docker-compose -f docker-compose.rag.yml restart worker"
echo "  (after setting USE_OPENROUTER back to false)"
echo ""
echo "Monitor usage at: https://openrouter.ai/activity"
echo ""

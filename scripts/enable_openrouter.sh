#!/bin/bash
# Quick script to enable OpenRouter for faster testing

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           OpenRouter Setup for Faster Testing                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Check if API key is provided
if [ -z "$1" ]; then
    echo "❌ Error: OpenRouter API key required"
    echo ""
    echo "Usage: ./enable_openrouter.sh YOUR_API_KEY"
    echo ""
    echo "How to get a free API key:"
    echo "1. Go to https://openrouter.ai/"
    echo "2. Sign up (free)"
    echo "3. Go to Settings → API Keys"
    echo "4. Create a new key"
    echo ""
    echo "Free models available:"
    echo "  - qwen/qwen-2-7b-instruct:free (recommended)"
    echo "  - google/gemma-2-9b-it:free"
    echo "  - meta-llama/llama-3-8b-instruct:free"
    echo "  - mistralai/mistral-7b-instruct:free"
    exit 1
fi

API_KEY=$1
MODEL=${2:-"qwen/qwen-2-7b-instruct:free"}

echo "✓ API Key: ${API_KEY:0:10}..."
echo "✓ Model: $MODEL"
echo ""

# Update docker-compose with OpenRouter settings
echo "Updating docker-compose.rag.yml..."

# Create a temporary backup
cp docker-compose.rag.yml docker-compose.rag.yml.backup

# Add OpenRouter environment variables to worker service
if grep -q "USE_OPENROUTER" docker-compose.rag.yml; then
    echo "  → OpenRouter config already exists, updating..."
    sed -i.bak "s|USE_OPENROUTER:.*|USE_OPENROUTER: \"true\"|" docker-compose.rag.yml
    sed -i.bak "s|OPENROUTER_API_KEY:.*|OPENROUTER_API_KEY: \"$API_KEY\"|" docker-compose.rag.yml
    sed -i.bak "s|OPENROUTER_MODEL:.*|OPENROUTER_MODEL: \"$MODEL\"|" docker-compose.rag.yml
else
    echo "  → Adding OpenRouter config..."
    # This would need manual editing of the file
    echo ""
    echo "Please add these lines to the 'worker_rag' environment section in docker-compose.rag.yml:"
    echo ""
    echo "      USE_OPENROUTER: \"true\""
    echo "      OPENROUTER_API_KEY: \"$API_KEY\""
    echo "      OPENROUTER_MODEL: \"$MODEL\""
    echo ""
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    Alternative: Manual Setup                     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Set these environment variables in docker-compose.rag.yml:"
echo ""
echo "  worker_rag:"
echo "    environment:"
echo "      USE_OPENROUTER: \"true\""
echo "      OPENROUTER_API_KEY: \"$API_KEY\""
echo "      OPENROUTER_MODEL: \"$MODEL\""
echo ""
echo "Then restart:"
echo "  docker-compose -f docker-compose.rag.yml restart worker_rag"
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                   Or: Quick Docker Command                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Run this command to enable OpenRouter immediately:"
echo ""
echo "docker exec llm_worker_rag sh -c 'export USE_OPENROUTER=true && export OPENROUTER_API_KEY=$API_KEY && export OPENROUTER_MODEL=$MODEL && python3 -m app.worker_rag'"
echo ""

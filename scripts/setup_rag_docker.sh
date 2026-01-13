#!/bin/bash
# Setup and test RAG system in Docker

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "RAG Docker Setup and Test"
echo "=========================================="
echo "Project directory: $PROJECT_DIR"

# Step 1: Build worker image
echo ""
echo "Step 1: Building worker image..."
docker-compose -f docker-compose.rag.yml build worker

# Step 2: Start services (RabbitMQ, Ollama)
echo ""
echo "Step 2: Starting RabbitMQ and Ollama..."
docker-compose -f docker-compose.rag.yml up -d rabbitmq ollama

# Wait for services to be ready
echo ""
echo "Waiting for services to start..."
sleep 10

# Step 3: Update RSS feeds
echo ""
echo "Step 3: Updating RSS feeds..."
docker-compose -f docker-compose.rag.yml run --rm rag_updater

# Step 4: Start RAG worker
echo ""
echo "Step 4: Starting RAG worker..."
docker-compose -f docker-compose.rag.yml up -d worker

# Wait for worker to start
sleep 5

# Step 5: Check status
echo ""
echo "Step 5: Checking service status..."
docker-compose -f docker-compose.rag.yml ps

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To test, run:"
echo "  python3 test_rag_docker.py"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.rag.yml logs -f worker"
echo ""

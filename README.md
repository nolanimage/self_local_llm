# Self LLM - RAG-Enhanced LLM System

A distributed LLM inference system with Retrieval-Augmented Generation (RAG) capabilities, using:
- **Ollama**: LLM serving with Metal GPU acceleration (Mac)
- **RabbitMQ**: Message queue for request/response handling
- **RAG System**: Local RSS feed storage with Chinese embeddings for semantic search
- **Docker**: Containerized deployment

## Architecture

```
Web Interface → RabbitMQ → Worker (RAG) → Ollama → Response → RabbitMQ → Web Interface
                      ↓
                  RSS Database
              (SQLite + Embeddings)
```

## Features

- ✅ **RAG-Enhanced Responses**: Retrieves relevant news articles to enhance LLM responses
- ✅ **Chinese Embeddings**: Uses BAAI/bge-m3 for excellent Chinese text understanding
- ✅ **Hybrid Search**: Combines semantic and keyword search for better results
- ✅ **Reranking**: Cross-encoder reranking for improved accuracy
- ✅ **Automatic Updates**: RSS feeds updated hourly automatically
- ✅ **Traditional Chinese Support**: Responds in Traditional Chinese for Chinese queries
- ✅ **Web Interface**: Streamlit-based chat interface

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run the quick start script
./QUICK_START.sh
```

This will:
- Check prerequisites
- Create `.env` file if needed
- Start all Docker services
- Pull Ollama model
- Start API server
- Set up web interface

### Option 2: Manual Setup

See **[INSTALLATION.md](INSTALLATION.md)** for detailed step-by-step instructions.

**Quick commands:**
```bash
# 1. Configure environment
cp config.env.example .env
# Edit .env with your secrets

# 2. Start Docker services
./scripts/setup_rag_docker.sh

# 3. Start API server (in new terminal)
python3 api_server.py

# 4. Start web interface (in another terminal)
cd web && npm install && npm run dev
```

**Access points:**
- Next.js Web Interface: http://localhost:3000
- Streamlit Web Interface: http://localhost:8501
- API Server: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Services

### RabbitMQ
- **Port**: 5672 (AMQP), 15672 (Management UI)
- **Credentials**: Set via `RABBITMQ_USER` and `RABBITMQ_PASS` environment variables
- **Management UI**: http://localhost:15672

### Ollama
- **Port**: 11434
- **Model**: qwen2.5:1.5b (configurable)
- **GPU**: Metal acceleration on Mac

### Worker (RAG)
- Processes requests with RAG enhancement
- Retrieves relevant articles from RSS database
- Generates context-aware responses

### RSS Updater
- Fetches RSS feeds hourly
- Generates embeddings for new articles
- Stores in SQLite database

## Configuration

### Environment Variables

Create a `.env` file from `config.env.example`:

```bash
cp config.env.example .env
# Edit .env with your actual secrets
```

Required environment variables:

```bash
# Security (REQUIRED - change from defaults!)
RABBITMQ_USER=admin
RABBITMQ_PASS=your_secure_password_here

# OpenRouter (optional, for faster testing)
OPENROUTER_API_KEY=your_api_key_here
USE_OPENROUTER=false

# Ollama model
OLLAMA_MODEL=qwen2.5:1.5b

# Embedding model (default: BAAI/bge-m3)
EMBEDDING_MODEL=BAAI/bge-m3

# RAG settings
RAG_USE_HYBRID=false
RAG_USE_RERANK=true
RAG_MIN_SIMILARITY=0.3

# RSS update interval (seconds)
RSS_UPDATE_INTERVAL=3600
```

### Security

⚠️ **IMPORTANT**: Before running in production:

1. **Change default passwords**: Update `RABBITMQ_PASS` in your `.env` file
2. **Never commit secrets**: The `.gitignore` excludes `.env` files - never commit them
3. **Use environment variables**: All secrets are loaded from environment variables, not hardcoded
4. **Review access**: RabbitMQ management UI should not be exposed publicly

See `config.env.example` for all available configuration options.

### RSS Feeds

Default feeds (RTHK):
- Local news
- Greater China news
- International news
- Finance news
- Sports news

To customize, set `RSS_FEEDS` environment variable in `docker-compose.rag.yml`.

## Documentation

- **docs/RAG_SETUP.md**: Detailed RAG system setup and configuration
- **docs/UPGRADE_GUIDE.md**: How to upgrade models and features
- **docs/IMPROVE_MATCHING.md**: Methods to improve RAG matching accuracy
- **docs/TROUBLESHOOTING.md**: Common issues and solutions
- **docs/SECURITY.md**: Security guide and best practices

## Usage

### Web Interface

1. Start the web interface: `./scripts/start_web_interface.sh`
2. Open http://localhost:8501
3. Type your query (supports Chinese and English)
4. System will automatically:
   - Detect language
   - Retrieve relevant articles
   - Generate context-aware response

### Python Client

```python
from app.client import LLMClient

client = LLMClient()

response = client.generate(
    prompt="香港最新新聞",
    max_tokens=300,
    temperature=0.7
)

print(response['response'])
client.close()
```

## Monitoring

### Check Service Status

```bash
docker-compose -f docker-compose.rag.yml ps
```

### View Logs

```bash
# Worker logs
docker logs llm_worker_rag -f

# RSS updater logs
docker logs rag_updater -f

# All services
docker-compose -f docker-compose.rag.yml logs -f
```

### Check Database

```bash
docker exec llm_worker_rag python3 -c "
from app.rag_system import RAGSystem
rag = RAGSystem()
print(f'Total articles: {rag.get_article_count()}')
"
```

## Stopping Services

```bash
docker-compose -f docker-compose.rag.yml down
```

To remove volumes (clears database and cache):

```bash
docker-compose -f docker-compose.rag.yml down -v
```


## License

MIT

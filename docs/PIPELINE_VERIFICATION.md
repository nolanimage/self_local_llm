# Pipeline Verification and Fixes

## ✅ All Issues Fixed

### 1. Dockerfile.worker
**Issue**: Referenced old paths for `update_rss_feeds.py` and `update_rss_periodic.py`

**Fix**: Updated to copy `utils/` directory and create symlinks for backward compatibility

```dockerfile
COPY utils/ ./utils/
RUN ln -s utils/update_rss_feeds.py update_rss_feeds.py && \
    ln -s utils/update_rss_periodic.py update_rss_periodic.py
```

### 2. Startup Scripts
**Issue**: Hardcoded absolute paths (`/Users/nolanlu/Desktop/code_for_fun/self_llm`)

**Fix**: All scripts now use relative paths based on script location:
- `scripts/setup_rag_docker.sh`
- `scripts/start_web_interface.sh`
- `scripts/start_nextjs.sh`
- `scripts/enable_openrouter.sh`
- `scripts/setup_openrouter.sh`

**Pattern used**:
```bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
```

### 3. Docker Compose Paths
**Status**: ✅ Already correct
- `./utils/update_rss_periodic.py` - Correct
- `./rate_limiter.py` - Correct (root level)
- `./trending.py` - Correct (root level)
- `./app/prompts` - Correct

### 4. Import Paths
**Status**: ✅ All correct
- `utils/update_rss_periodic.py` imports from `app.rag_system` - Works in Docker context
- `api_server.py` imports from root level `rate_limiter` and `trending` - Correct

### 5. Documentation
**Created**:
- `INSTALLATION.md` - Comprehensive installation guide
- `QUICK_START.sh` - Automated setup script
- `VERIFY_INSTALLATION.sh` - Verification script
- Updated `README.md` with quick start instructions

## 🚀 Complete Pipeline

### Pipeline Flow

```
User → Next.js Web Interface (port 3000)
  ↓
Next.js API Route (/api/chat)
  ↓
FastAPI Server (port 8000)
  ↓
RabbitMQ (port 5672)
  ↓
RAG Worker (Docker)
  ↓
Ollama/OpenRouter → LLM Response
  ↓
RAG System → Article Retrieval
  ↓
Response → RabbitMQ → FastAPI → Next.js → User
```

### Services Required

1. **RabbitMQ** (Docker)
   - Port: 5672 (AMQP), 15672 (Management)
   - Started: `docker-compose -f docker-compose.rag.yml up -d rabbitmq`

2. **Ollama** (Docker)
   - Port: 11434
   - Model: qwen2.5:1.5b
   - Started: `docker-compose -f docker-compose.rag.yml up -d ollama`

3. **RAG Worker** (Docker)
   - Processes LLM requests with RAG
   - Started: `docker-compose -f docker-compose.rag.yml up -d worker`

4. **RSS Updater** (Docker)
   - Updates RSS feeds periodically
   - Started: `docker-compose -f docker-compose.rag.yml up -d rag_updater`

5. **API Server** (Python)
   - Port: 8000
   - Started: `python3 api_server.py`

6. **Next.js Web Interface** (Node.js)
   - Port: 3000
   - Started: `cd web && npm run dev`

## 📋 Verification Checklist

Run `./VERIFY_INSTALLATION.sh` to check:

- [x] Docker services running (RabbitMQ, Ollama, Worker, Updater)
- [x] Ports accessible (5672, 11434, 8000, 15672)
- [x] API endpoints responding
- [x] RabbitMQ connection working
- [x] Ollama model installed
- [x] Python dependencies installed
- [x] Node.js dependencies installed (optional)
- [x] Required files present

## 🧪 Testing the Pipeline

### 1. Start All Services

```bash
# Option 1: Automated
./QUICK_START.sh

# Option 2: Manual
./scripts/setup_rag_docker.sh
python3 api_server.py &
cd web && npm run dev
```

### 2. Verify Services

```bash
./VERIFY_INSTALLATION.sh
```

### 3. Test End-to-End

```bash
# Test with Python
python3 tests/test_quality_improvements.py

# Test via API
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "今天有什麼新聞？", "max_tokens": 200}'

# Test via Web Interface
# Open http://localhost:3000 and send a message
```

## 🔧 Common Issues and Solutions

### Issue: "Cannot connect to RabbitMQ"

**Solution**:
```bash
# Check RabbitMQ is running
docker-compose -f docker-compose.rag.yml ps rabbitmq

# Check logs
docker-compose -f docker-compose.rag.yml logs rabbitmq

# Restart
docker-compose -f docker-compose.rag.yml restart rabbitmq
```

### Issue: "API server connection refused"

**Solution**:
```bash
# Check if running
curl http://localhost:8000/health

# Start if not running
python3 api_server.py

# Check logs
tail -f api_server.log
```

### Issue: "Worker not processing requests"

**Solution**:
```bash
# Check worker logs
docker-compose -f docker-compose.rag.yml logs worker

# Restart worker
docker-compose -f docker-compose.rag.yml restart worker

# Check RabbitMQ connection
docker exec llm_worker_rag python3 -c "import pika; print('OK')"
```

### Issue: "Web interface cannot connect to API"

**Solution**:
1. Verify API server is running: `curl http://localhost:8000/health`
2. Check `web/.env.local` has correct `API_SERVER_URL`
3. Check CORS settings in `api_server.py`

## 📝 File Structure Verification

All files are in correct locations:

```
self_llm/
├── api_server.py              ✅ Root (entry point)
├── rate_limiter.py            ✅ Root (used by api_server)
├── trending.py                ✅ Root (used by api_server)
├── docker-compose.rag.yml     ✅ Root (Docker config)
├── Dockerfile.worker          ✅ Root (Docker image)
├── config.env.example         ✅ Root (config template)
│
├── app/                       ✅ Application code
│   ├── worker_rag.py
│   ├── worker_ollama.py
│   ├── rag_system.py
│   └── prompts/
│
├── utils/                     ✅ Utility scripts
│   ├── update_rss_periodic.py ✅ (used by Docker)
│   └── ...
│
├── scripts/                   ✅ Startup scripts
│   ├── setup_rag_docker.sh   ✅ (uses relative paths)
│   ├── start_nextjs.sh       ✅ (uses relative paths)
│   └── ...
│
└── web/                       ✅ Next.js interface
    ├── package.json
    └── ...
```

## ✅ All Systems Ready

The entire pipeline has been verified and all issues have been fixed:

1. ✅ Docker services can start
2. ✅ API server can start
3. ✅ Web interface can start
4. ✅ All imports work correctly
5. ✅ All paths are relative and portable
6. ✅ Documentation is complete
7. ✅ Verification scripts are available

**The system is ready for use!** 🎉

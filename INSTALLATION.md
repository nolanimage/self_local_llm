# Installation and Startup Guide

Complete guide to install, configure, and start the Self LLM RAG system.

## 📋 Prerequisites

### Required Software
- **Docker** and **Docker Compose** (for backend services)
- **Python 3.10+** (for API server and utilities)
- **Node.js 18+** and **npm** (for Next.js web interface)
- **Git** (to clone the repository)

### System Requirements
- **macOS** (M-series chip recommended for Metal GPU acceleration)
- **16GB+ RAM** (for Docker containers)
- **10GB+ free disk space** (for models and Docker images)

## 🚀 Quick Start

### Option 1: Full Docker Setup (Recommended)

```bash
# 1. Clone or navigate to the project
cd self_llm

# 2. Create environment file
cp config.env.example .env
# Edit .env with your secrets (especially RABBITMQ_PASS)

# 3. Start all services
./scripts/setup_rag_docker.sh

# 4. Start API server (in a new terminal)
python3 api_server.py

# 5. Start web interface (in another terminal)
cd web
npm install  # First time only
npm run dev
```

### Option 2: Manual Setup

See detailed steps below.

## 📦 Step-by-Step Installation

### Step 1: Install Dependencies

#### Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install Python packages
pip install -r requirements.txt
```

#### Node.js Dependencies

```bash
cd web
npm install
```

### Step 2: Configure Environment

```bash
# Copy example config
cp config.env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Required settings in `.env`:**
```env
# Security (REQUIRED - change from defaults!)
RABBITMQ_USER=admin
RABBITMQ_PASS=your_secure_password_here

# OpenRouter (optional, for faster testing)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
USE_OPENROUTER=false

# Ollama model
OLLAMA_MODEL=qwen2.5:1.5b

# Embedding model
EMBEDDING_MODEL=BAAI/bge-m3
```

### Step 3: Start Docker Services

```bash
# Start RabbitMQ and Ollama
docker-compose -f docker-compose.rag.yml up -d rabbitmq ollama

# Wait for services to be ready
sleep 10

# Pull Ollama model (first time only)
docker exec ollama_server ollama pull qwen2.5:1.5b

# Start worker and RSS updater
docker-compose -f docker-compose.rag.yml up -d worker rag_updater
```

### Step 4: Start API Server

```bash
# Activate virtual environment if using one
source venv/bin/activate

# Start API server
python3 api_server.py

# Or run in background
nohup python3 api_server.py > api_server.log 2>&1 &
```

The API server will be available at `http://localhost:8000`

### Step 5: Start Web Interface

#### Option A: Next.js (Modern Interface)

```bash
cd web

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Access at: `http://localhost:3000`

#### Option B: Streamlit (Legacy Interface)

```bash
streamlit run web_interface.py
```

Access at: `http://localhost:8501`

## 🔧 Startup Scripts

All startup scripts are in the `scripts/` directory:

### `scripts/setup_rag_docker.sh`
Complete Docker setup:
- Builds worker image
- Starts RabbitMQ and Ollama
- Updates RSS feeds
- Starts RAG worker

```bash
./scripts/setup_rag_docker.sh
```

### `scripts/start_nextjs.sh`
Starts Next.js web interface and API server:
- Checks if API server is running
- Starts API server if needed
- Starts Next.js dev server

```bash
./scripts/start_nextjs.sh
```

### `scripts/start_web_interface.sh`
Starts Streamlit web interface:

```bash
./scripts/start_web_interface.sh
```

### `scripts/enable_openrouter.sh`
Interactive setup for OpenRouter API:

```bash
./scripts/enable_openrouter.sh [API_KEY]
```

## ✅ Verification

### Check Docker Services

```bash
# Check all services
docker-compose -f docker-compose.rag.yml ps

# Check logs
docker-compose -f docker-compose.rag.yml logs -f worker
```

### Check API Server

```bash
# Health check
curl http://localhost:8000/health

# RAG stats
curl http://localhost:8000/api/rag/stats
```

### Check Web Interface

Open in browser:
- Next.js: `http://localhost:3000`
- Streamlit: `http://localhost:8501`

## 🔄 Full Pipeline Test

### 1. Test Backend Services

```bash
# Test RabbitMQ
curl http://localhost:15672  # Management UI

# Test Ollama
curl http://localhost:11434/api/tags

# Test API Server
curl http://localhost:8000/health
```

### 2. Test RAG System

```bash
# Run test script
python3 tests/test_quality_improvements.py
```

### 3. Test Web Interface

1. Open `http://localhost:3000` (Next.js) or `http://localhost:8501` (Streamlit)
2. Enter a query: "今天有什麼新聞？"
3. Verify response appears with RAG enhancement

## 🐛 Troubleshooting

### Docker Issues

**Problem**: Services won't start

**Solution**:
```bash
# Check Docker is running
docker ps

# Check logs
docker-compose -f docker-compose.rag.yml logs

# Restart services
docker-compose -f docker-compose.rag.yml restart
```

**Problem**: Port already in use

**Solution**:
```bash
# Find process using port
lsof -i :8000  # For API server
lsof -i :5672  # For RabbitMQ

# Kill process or change port in docker-compose.rag.yml
```

### Python Import Errors

**Problem**: `ModuleNotFoundError`

**Solution**:
```bash
# Ensure you're in project root
cd /path/to/self_llm

# Install dependencies
pip install -r requirements.txt

# Check Python path
python3 -c "import sys; print(sys.path)"
```

### API Server Issues

**Problem**: API server won't start

**Solution**:
```bash
# Check RabbitMQ is running
docker-compose -f docker-compose.rag.yml ps rabbitmq

# Check environment variables
echo $RABBITMQ_PASS

# Check logs
tail -f api_server.log
```

### Web Interface Issues

**Problem**: Next.js won't start

**Solution**:
```bash
cd web

# Clear cache
rm -rf .next node_modules

# Reinstall
npm install

# Try again
npm run dev
```

**Problem**: Cannot connect to API

**Solution**:
- Verify API server is running: `curl http://localhost:8000/health`
- Check `API_SERVER_URL` in `web/.env.local`
- Check CORS settings in `api_server.py`

## 📝 Environment Variables Reference

### Required
- `RABBITMQ_USER` - RabbitMQ username (default: admin)
- `RABBITMQ_PASS` - RabbitMQ password (⚠️ change from default!)

### Optional
- `USE_OPENROUTER` - Use OpenRouter instead of Ollama (true/false)
- `OPENROUTER_API_KEY` - OpenRouter API key
- `OPENROUTER_MODEL` - OpenRouter model name
- `OLLAMA_MODEL` - Ollama model name (default: qwen2.5:1.5b)
- `EMBEDDING_MODEL` - Embedding model (default: BAAI/bge-m3)
- `RAG_USE_RERANK` - Enable reranking (true/false)
- `RAG_MIN_SIMILARITY` - Minimum similarity threshold (0.0-1.0)

## 🎯 Common Workflows

### Daily Startup

```bash
# 1. Start Docker services
docker-compose -f docker-compose.rag.yml up -d

# 2. Start API server
python3 api_server.py &

# 3. Start web interface
cd web && npm run dev
```

### Development Workflow

```bash
# Terminal 1: Docker services
docker-compose -f docker-compose.rag.yml up

# Terminal 2: API server
python3 api_server.py

# Terminal 3: Web interface
cd web && npm run dev

# Terminal 4: Tests
python3 tests/test_quality_improvements.py
```

### Production Deployment

1. Set strong passwords in `.env`
2. Use HTTPS (reverse proxy)
3. Run API server as service (systemd/PM2)
4. Build Next.js for production: `cd web && npm run build && npm start`
5. Monitor logs and resources

## 📚 Next Steps

- Read `README.md` for system overview
- Check `docs/SECURITY.md` for security best practices
- Review `docs/RAG_SETUP.md` for RAG configuration
- See `docs/TROUBLESHOOTING.md` for more help

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `docker-compose -f docker-compose.rag.yml logs`
2. Review troubleshooting section above
3. Check GitHub issues
4. Review documentation in `docs/` directory

---

**Happy coding! 🚀**

# System Upgrade Guide

## Current System Configuration

### LLM Model
- **Current**: `qwen2.5:1.5b` (~1GB)
- **Location**: Configured in `app/worker_ollama.py` and `docker-compose.rag.yml`

### Embedding Model
- **Current**: `all-MiniLM-L6-v2` (22MB, 384-dim)
- **Location**: `app/rag_system.py`

### Dependencies
- Python packages: See `requirements.txt`
- Docker images: Latest versions

---

## Upgrade Options

### 1. LLM Model Upgrades

#### Option A: Upgrade to Larger Qwen Models (Recommended for Chinese)

```bash
# Pull larger Qwen model
docker exec ollama_server ollama pull qwen2.5:3b    # ~2GB, better quality
docker exec ollama_server ollama pull qwen2.5:7b    # ~4.5GB, high quality
docker exec ollama_server ollama pull qwen2.5:14b    # ~8GB, very high quality

# Update configuration
export OLLAMA_MODEL=qwen2.5:7b
docker-compose -f docker-compose.rag.yml up -d worker
```

**Performance Impact:**
- `qwen2.5:3b`: 2-4s response time, better Chinese understanding
- `qwen2.5:7b`: 3-6s response time, high quality responses
- `qwen2.5:14b`: 5-10s response time, best quality

#### Option B: Upgrade to Other High-Quality Models

```bash
# Llama 3 (excellent general purpose)
docker exec ollama_server ollama pull llama3:8b     # ~4.7GB
docker exec ollama_server ollama pull llama3:70b    # ~40GB (requires significant RAM)

# Mistral (great for reasoning)
docker exec ollama_server ollama pull mistral:7b    # ~4.1GB

# DeepSeek (excellent for Chinese)
docker exec ollama_server ollama pull deepseek-r1:7b  # ~4.5GB

# Update worker
export OLLAMA_MODEL=llama3:8b
docker-compose -f docker-compose.rag.yml up -d worker
```

#### Option C: Use Quantized Models (Faster, Smaller)

```bash
# Quantized versions (smaller, faster, slightly lower quality)
docker exec ollama_server ollama pull qwen2.5:7b-q4_0  # 4-bit quantization
docker exec ollama_server ollama pull llama3:8b-q4_0

export OLLAMA_MODEL=qwen2.5:7b-q4_0
docker-compose -f docker-compose.rag.yml up -d worker
```

---

### 2. Embedding Model Upgrades

#### Option A: Better Multilingual Support

```bash
# Upgrade to better Chinese embedding model
export EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
docker-compose -f docker-compose.rag.yml build worker
docker-compose -f docker-compose.rag.yml up -d worker
```

**Benefits:**
- Better Chinese text understanding
- Improved semantic search accuracy
- Size: 420MB (vs 22MB current)

#### Option B: Advanced Multilingual Model (Best for Chinese)

```bash
# Use BAAI/bge-m3 (requires FlagEmbedding)
# Update requirements.txt first:
# flag-embedding>=1.2.0

# Then update app/rag_system.py to use FlagEmbedding
export EMBEDDING_MODEL=BAAI/bge-m3
docker-compose -f docker-compose.rag.yml build worker
docker-compose -f docker-compose.rag.yml up -d worker
```

**Benefits:**
- Excellent Chinese performance
- Supports 100+ languages
- Dense + sparse + multi-vector retrieval
- Size: ~2GB

#### Option C: OpenAI-Compatible Embeddings

```bash
# Use OpenAI embeddings (requires API key)
# Update app/rag_system.py to support OpenAI API
export OPENAI_API_KEY=your_key_here
export EMBEDDING_PROVIDER=openai
```

---

### 3. Dependency Upgrades

#### Update Python Packages

```bash
# Update requirements.txt with latest versions
pip install --upgrade pika requests openai streamlit feedparser sentence-transformers numpy

# Rebuild Docker image
docker-compose -f docker-compose.rag.yml build worker
```

#### Recommended Versions

```txt
pika>=1.3.2
requests>=2.31.0
openai>=1.12.0
streamlit>=1.28.0
feedparser>=6.0.10
sentence-transformers>=2.2.2
numpy>=1.24.3
huggingface-hub>=0.20.0
```

---

### 4. Feature Upgrades

#### A. Add More RSS Feeds

```bash
# Add multiple RSS feeds
export RSS_FEEDS="https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_clocal.xml,https://example.com/feed.xml,https://another.com/feed.xml"
docker-compose -f docker-compose.rag.yml up -d rag_updater
```

#### B. Improve RAG Search

Update `app/rag_system.py`:
- Increase `top_k` from 2 to 5 for more context
- Add reranking for better results
- Implement hybrid search (keyword + semantic)

#### C. Add Streaming Responses

Update `app/worker_rag.py` to support streaming:
```python
"stream": True  # Enable streaming
```

#### D. Add Response Caching

Implement caching for frequent queries to reduce LLM calls.

---

### 5. Performance Upgrades

#### A. Increase Context Window

```python
# In app/worker_rag.py
"num_ctx": 2048,  # Increase from 1024
```

#### B. Enable GPU Acceleration (Mac)

```bash
# Ensure Ollama uses Metal GPU
export OLLAMA_NUM_GPU=1
docker-compose -f docker-compose.rag.yml up -d ollama
```

#### C. Add Multiple Workers

```yaml
# In docker-compose.rag.yml, add:
worker2:
  # ... same config as worker
  environment:
    - WORKER_ID=2
```

#### D. Optimize Database

```python
# Add indexes to SQLite database
# In app/rag_system.py, add:
cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON articles(title)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON articles(created_at)")
```

---

### 6. System Architecture Upgrades

#### A. Add Vector Database (Advanced)

Replace SQLite with:
- **Chroma**: Lightweight, easy to use
- **Qdrant**: High performance
- **Pinecone**: Managed service
- **Weaviate**: Full-featured

#### B. Add Monitoring

```bash
# Add Prometheus + Grafana
# Monitor: response times, queue depth, model usage
```

#### C. Add Authentication

```python
# Add API keys or OAuth to web interface
# Update web_interface.py
```

---

## Quick Upgrade Commands

### Upgrade to Better Quality (Recommended)

```bash
# 1. Pull better LLM model
docker exec ollama_server ollama pull qwen2.5:7b

# 2. Pull better embedding model (optional, requires rebuild)
# Will use paraphrase-multilingual-MiniLM-L12-v2

# 3. Update worker
export OLLAMA_MODEL=qwen2.5:7b
export EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
docker-compose -f docker-compose.rag.yml build worker
docker-compose -f docker-compose.rag.yml up -d worker

# 4. Verify
docker logs llm_worker_rag --tail 20
```

### Upgrade to Production Quality

```bash
# 1. Pull production models
docker exec ollama_server ollama pull llama3:8b

# 2. Update all services
export OLLAMA_MODEL=llama3:8b
export EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
docker-compose -f docker-compose.rag.yml build
docker-compose -f docker-compose.rag.yml up -d

# 3. Increase resources in Docker Desktop
# - Memory: 16GB+ recommended
# - CPU: 4+ cores
```

### Minimal Upgrade (Keep Small, Better Quality)

```bash
# Just upgrade LLM to 3B model
docker exec ollama_server ollama pull qwen2.5:3b
export OLLAMA_MODEL=qwen2.5:3b
docker-compose -f docker-compose.rag.yml up -d worker
```

---

## Upgrade Checklist

- [ ] Backup current configuration
- [ ] Check available disk space (models can be large)
- [ ] Check Docker memory allocation
- [ ] Pull new model
- [ ] Update environment variables
- [ ] Rebuild containers if needed
- [ ] Test with sample queries
- [ ] Monitor performance
- [ ] Update documentation

---

## Rollback Plan

If upgrade causes issues:

```bash
# Revert to previous model
export OLLAMA_MODEL=qwen2.5:1.5b
docker-compose -f docker-compose.rag.yml up -d worker

# Or restore from backup
git checkout app/worker_ollama.py
docker-compose -f docker-compose.rag.yml build worker
```

---

## Recommendations by Use Case

### Development/Testing
- **LLM**: `qwen2.5:1.5b` (current) or `qwen2.5:3b`
- **Embedding**: `all-MiniLM-L6-v2` (current)
- **Why**: Fast, small, sufficient for testing

### Production (Chinese Focus)
- **LLM**: `qwen2.5:7b` or `qwen2.5:14b`
- **Embedding**: `paraphrase-multilingual-MiniLM-L12-v2` or `BAAI/bge-m3`
- **Why**: Best Chinese understanding and quality

### Production (General Purpose)
- **LLM**: `llama3:8b` or `mistral:7b`
- **Embedding**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Why**: Excellent general performance

### Maximum Quality
- **LLM**: `llama3:70b` or `qwen2.5:32b`
- **Embedding**: `BAAI/bge-m3`
- **Why**: Best possible quality (requires significant resources)

---

## Monitoring After Upgrade

```bash
# Check response times
docker logs llm_worker_rag | grep "completed successfully"

# Check memory usage
docker stats llm_worker_rag ollama_server

# Test RAG search
docker exec llm_worker_rag python3 -c "from app.rag_system import RAGSystem; r = RAGSystem(); print(r.search_articles('香港', top_k=3))"
```

---

## Need Help?

- Check logs: `docker logs llm_worker_rag`
- Test model: `docker exec ollama_server ollama list`
- Verify config: `docker exec llm_worker_rag env | grep OLLAMA_MODEL`

# RAG System Setup

## Overview

Retrieval-Augmented Generation (RAG) system that stores RSS feeds locally and uses Chinese embeddings for semantic search. The system is already configured with advanced features: BAAI/bge-m3 embeddings, hybrid search, and reranking.

## Features

- ✅ RSS feed storage (SQLite database)
- ✅ Chinese text embeddings (BAAI/bge-m3 - best for Chinese)
- ✅ Semantic search for relevant articles
- ✅ Hybrid search (semantic + keyword)
- ✅ Reranking with cross-encoder
- ✅ Integration with LLM worker for enhanced responses
- ✅ Automatic RSS feed updates (hourly)

## Quick Start

### 1. Start Services

```bash
# Start all services
docker-compose -f docker-compose.rag.yml up -d

# Or use setup script
./setup_rag_docker.sh
```

### 2. Verify RSS Updater

The RSS updater runs automatically and fetches new articles every hour. Check logs:

```bash
docker logs rag_updater -f
```

### 3. Test the System

The system is ready to use! Query through the web interface or worker.

## Current Configuration

### Embedding Model: BAAI/bge-m3

- **Best for Chinese** and multilingual (100+ languages)
- 1024-dimensional embeddings
- Supports up to 8192 tokens
- Dense + sparse + multi-vector retrieval
- **Expected similarity scores**: 0.6-0.85 (vs 0.3-0.6 with basic models)

### Hybrid Search

- Combines semantic search (70% weight) + keyword search (30% weight)
- Better coverage of relevant articles
- Finds articles that pure semantic search might miss

### Reranking

- Uses `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Better ranking accuracy than cosine similarity alone
- Final score: 40% hybrid + 60% rerank

## Database Schema

- `articles` table stores:
  - title, content, link, pub_date, source
  - embedding (binary blob, 1024 dimensions)
  - created_at timestamp

## RSS Feeds

Default feeds (RTHK):
- Local news: `https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_clocal.xml`
- Greater China: `https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_greaterchina.xml`
- International: `https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_cinternational.xml`
- Finance: `https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_cfinance.xml`
- Sports: `https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_csport.xml`

To customize, set `RSS_FEEDS` environment variable in `docker-compose.rag.yml`.

## Configuration

### Environment Variables

```bash
# Embedding model (default: BAAI/bge-m3)
export EMBEDDING_MODEL=BAAI/bge-m3

# Enable hybrid search (default: true)
export RAG_USE_HYBRID=true

# Enable reranking (default: true)
export RAG_USE_RERANK=true

# Minimum similarity threshold (default: 0.3)
export RAG_MIN_SIMILARITY=0.3

# RSS update interval (seconds, default: 3600 = 1 hour)
export RSS_UPDATE_INTERVAL=3600
```

### Disable Features (if needed)

```bash
# Disable hybrid search (use only semantic)
export RAG_USE_HYBRID=false

# Disable reranking (use only cosine similarity)
export RAG_USE_RERANK=false
```

## How It Works

### Search Flow

```
User Query
     ↓
[Generate Query Embedding with BAAI/bge-m3]
     ↓
[Hybrid Search]
  ├─ Semantic Search (70% weight)
  │   └─ Compare with stored embeddings
  │
  └─ Keyword Search (30% weight)
      └─ SQL LIKE matching
     ↓
[Combine Scores]
     ↓
[Reranking with Cross-Encoder]
  └─ Better ranking accuracy
     ↓
[Filter by Min Similarity]
     ↓
Top-K Results → LLM Context
```

### Scoring

1. **Semantic Score**: Cosine similarity (0.0 to 1.0)
2. **Keyword Score**: Match count (normalized)
3. **Hybrid Score**: 0.7 × semantic + 0.3 × keyword
4. **Rerank Score**: Cross-encoder prediction (normalized to 0-1)
5. **Final Score**: 0.4 × hybrid + 0.6 × rerank

## Manual RSS Update

If you need to manually update RSS feeds:

```bash
# Run updater once
docker-compose -f docker-compose.rag.yml run --rm rag_updater

# Or locally
python3 update_rss_feeds.py
```

## Re-embedding Articles

If you switch embedding models, you need to re-embed all articles:

```bash
docker exec llm_worker_rag python3 /app/re_embed_articles.py
```

## Testing

### Test Search

```bash
docker exec llm_worker_rag python3 << 'PYEOF'
from app.rag_system import RAGSystem
rag = RAGSystem()

# Test search
results = rag.search_articles('香港', top_k=3)
for i, r in enumerate(results, 1):
    print(f"{i}. {r['title'][:50]}...")
    print(f"   Similarity: {r.get('similarity', r.get('hybrid_score', 0)):.4f}")
PYEOF
```

### Check Article Count

```bash
docker exec llm_worker_rag python3 -c "
from app.rag_system import RAGSystem
print(f'Total articles: {RAGSystem().get_article_count()}')
"
```

## Troubleshooting

### Embedding Dimension Mismatch

If you see errors about embedding dimensions:
- Old embeddings: 384-dim (all-MiniLM-L6-v2)
- New embeddings: 1024-dim (BAAI/bge-m3)

**Solution**: Re-embed all articles (see "Re-embedding Articles" above)

### FlagEmbedding not found

```bash
# Check if installed
docker exec llm_worker_rag pip list | grep -i flag

# Reinstall
docker exec llm_worker_rag pip install git+https://github.com/FlagOpen/FlagEmbedding.git
```

### Reranker not loading

```bash
# Check if cross-encoder is available
docker exec llm_worker_rag python3 -c "from sentence_transformers import CrossEncoder; print('OK')"

# Fallback: Disable reranking
export RAG_USE_RERANK=false
```

## Performance Expectations

### With BAAI/bge-m3 + Reranking + Hybrid Search

- Similarity scores: 0.6-0.85
- Chinese understanding: Excellent
- Ranking: Cross-encoder reranking
- Coverage: Semantic + keyword

### Rollback to Simpler Model

If you need to use a simpler model:

```bash
# Use simpler model
export EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
export RAG_USE_HYBRID=false
export RAG_USE_RERANK=false

docker-compose -f docker-compose.rag.yml build worker
docker-compose -f docker-compose.rag.yml up -d worker
```

## Monitoring

### Check Embedding Model

```bash
docker logs llm_worker_rag | grep -i "embedding\|bge-m3"
```

### Check Search Performance

```bash
docker logs llm_worker_rag | grep -i "similarity\|rerank\|hybrid"
```

### Check RSS Updater

```bash
docker logs rag_updater -f
```

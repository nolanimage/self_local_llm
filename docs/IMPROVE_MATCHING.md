# How to Increase Matching Probability in RAG System

## Current Situation

The RAG system uses:
- **Embedding Model**: `all-MiniLM-L6-v2` (22MB, 384-dim)
- **Text Truncation**: 400 chars for Chinese, 512 for English
- **Similarity**: Cosine similarity
- **Current Scores**: Typically 0.3-0.6 for good matches

## Methods to Improve Matching Probability

### 1. Upgrade Embedding Model (Most Effective) ⭐

**Current**: `all-MiniLM-L6-v2` (basic multilingual support)
**Better Options**:

#### Option A: Better Multilingual Model
```bash
export EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
docker-compose -f docker-compose.rag.yml build worker
docker-compose -f docker-compose.rag.yml up -d worker
```
- **Size**: 420MB (vs 22MB)
- **Dimension**: 384-dim
- **Benefit**: Much better Chinese understanding
- **Expected Improvement**: +0.1-0.2 similarity score

#### Option B: Best Chinese Model (Recommended)
```bash
# Install FlagEmbedding first
pip install git+https://github.com/FlagOpen/FlagEmbedding.git

# Update app/rag_system.py to use FlagEmbedding
export EMBEDDING_MODEL=BAAI/bge-m3
```
- **Size**: ~2GB
- **Dimension**: 1024-dim (dense) + sparse + multi-vector
- **Benefit**: Excellent Chinese performance, best for multilingual
- **Expected Improvement**: +0.2-0.3 similarity score

### 2. Increase Text Length for Embeddings

**Current**: 400 chars for Chinese (truncated)
**Improvement**: Increase to 800-1000 chars

```python
# In app/rag_system.py, line 100
max_chars = 800 if any('\u4e00' <= c <= '\u9fff' for c in text) else 1000
```

**Benefit**: More context = better embeddings
**Trade-off**: Slightly slower, more memory

### 3. Improve Text Preprocessing

Add text cleaning before embedding:

```python
def preprocess_text(self, text: str) -> str:
    """Clean and normalize text for better embeddings"""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove special characters (keep Chinese, English, numbers)
    import re
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
    return text.strip()
```

### 4. Use Hybrid Search (Keyword + Semantic)

Combine semantic search with keyword matching:

```python
def hybrid_search(self, query: str, top_k: int = 3):
    """Combine semantic and keyword search"""
    # Semantic search
    semantic_results = self.search_articles(query, top_k=top_k*2)
    
    # Keyword search
    keyword_results = self.keyword_search(query, top_k=top_k*2)
    
    # Combine and rerank
    combined = self.combine_results(semantic_results, keyword_results)
    return combined[:top_k]
```

### 5. Add Reranking

Use a cross-encoder for better ranking:

```python
# Install: pip install sentence-transformers[extra]
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank_results(self, query: str, results: List[Dict], top_k: int):
    """Rerank results using cross-encoder"""
    pairs = [[query, r['content']] for r in results]
    scores = reranker.predict(pairs)
    
    for i, result in enumerate(results):
        result['rerank_score'] = float(scores[i])
    
    results.sort(key=lambda x: x['rerank_score'], reverse=True)
    return results[:top_k]
```

### 6. Normalize Embeddings Better

Ensure embeddings are properly normalized:

```python
# In get_embedding, already normalized:
embedding = self.embedding_model.encode(
    text,
    normalize_embeddings=True,  # ✓ Already enabled
    ...
)
```

### 7. Use Multiple Query Variations

Expand query with synonyms/related terms:

```python
def expand_query(self, query: str) -> str:
    """Expand query with related terms"""
    # For Chinese, add common synonyms
    expansions = {
        '香港': '香港 港 香港特別行政區',
        '新聞': '新聞 消息 資訊',
        '經濟': '經濟 金融 財經',
    }
    
    for key, expansion in expansions.items():
        if key in query:
            return f"{query} {expansion}"
    return query
```

### 8. Increase Top-K During Search

Search more articles, then filter:

```python
# In search_articles, increase initial search
results = self.search_articles(query, top_k=10)  # Instead of 3
# Then filter by minimum similarity threshold
filtered = [r for r in results if r['similarity'] > 0.3]
return filtered[:top_k]
```

### 9. Fine-tune Embedding Model (Advanced)

Fine-tune on your specific domain:

```python
# Requires training data
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

model = SentenceTransformer('all-MiniLM-L6-v2')
train_examples = [
    InputExample(texts=['香港', '香港特別行政區'], label=1.0),
    # Add more training pairs
]
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.CosineSimilarityLoss(model)
model.fit(train_objectives=[(train_dataloader, train_loss)], epochs=1)
```

### 10. Use Better Similarity Metric

Try different similarity measures:

```python
# Current: Cosine similarity (good for normalized embeddings)
similarity = np.dot(query_embedding, article_embedding)

# Alternative: Euclidean distance (inverse)
distance = np.linalg.norm(query_embedding - article_embedding)
similarity = 1 / (1 + distance)  # Convert to similarity

# Alternative: Dot product (if not normalized)
similarity = np.dot(query_embedding, article_embedding)
```

## Quick Wins (Easy to Implement)

### Priority 1: Upgrade Embedding Model
```bash
# Best improvement with minimal code changes
export EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
docker-compose -f docker-compose.rag.yml build worker
docker-compose -f docker-compose.rag.yml up -d worker
```

### Priority 2: Increase Text Length
```python
# In app/rag_system.py, line 100
max_chars = 800 if any('\u4e00' <= c <= '\u9fff' for c in text) else 1000
```

### Priority 3: Add Minimum Similarity Threshold
```python
# In search_articles, filter low similarity results
results = [r for r in similarities if r['similarity'] > 0.3]
```

## Expected Improvements

| Method | Expected Improvement | Difficulty | Cost |
|--------|---------------------|------------|------|
| Upgrade to multilingual model | +0.1-0.2 | Easy | Medium (420MB) |
| Upgrade to BAAI/bge-m3 | +0.2-0.3 | Medium | High (2GB) |
| Increase text length | +0.05-0.1 | Easy | Low |
| Add reranking | +0.1-0.15 | Medium | Medium |
| Hybrid search | +0.05-0.1 | Medium | Low |
| Fine-tuning | +0.15-0.25 | Hard | High |

## Implementation Example

### Quick Implementation (Recommended)

```python
# Update app/rag_system.py

def get_embedding(self, text: str) -> np.ndarray:
    """Generate embedding with improved settings"""
    # Increase max chars for better context
    max_chars = 800 if any('\u4e00' <= c <= '\u9fff' for c in text) else 1000
    if len(text) > max_chars:
        text = text[:max_chars]
    
    embedding = self.embedding_model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=1,
        device='cpu'
    )
    return embedding.flatten()

def search_articles(self, query: str, top_k: int = 3, min_similarity: float = 0.3):
    """Search with minimum similarity threshold"""
    # ... existing code ...
    
    # Filter by minimum similarity
    filtered = [r for r in similarities if r['similarity'] >= min_similarity]
    results = filtered[:top_k]
    
    return results
```

## Testing Improvements

```python
# Test before and after
before_scores = [0.55, 0.52, 0.48]  # Current
after_scores = [0.70, 0.68, 0.65]   # After improvements

improvement = (sum(after_scores) - sum(before_scores)) / len(before_scores)
print(f"Average improvement: {improvement:.2f}")
```

## Recommended Action Plan

1. **Immediate** (5 minutes):
   - Increase text length to 800 chars
   - Add minimum similarity threshold (0.3)

2. **Short-term** (30 minutes):
   - Upgrade to `paraphrase-multilingual-MiniLM-L12-v2`
   - Rebuild and test

3. **Long-term** (if needed):
   - Consider BAAI/bge-m3 for best Chinese performance
   - Add reranking for critical queries
   - Implement hybrid search

## Monitoring

Track similarity scores over time:
```python
# Log similarity scores
logger.info(f"Query: {query}, Top similarity: {results[0]['similarity']:.4f}")
```

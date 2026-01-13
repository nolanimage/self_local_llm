"""
RAG System for RSS Feed Storage and Retrieval - ENHANCED VERSION
Implements: BM25 Hybrid Search, FAISS Vector DB, Smart Chunking, 
Batch Embeddings, Entity Extraction, Multi-Query, Caching
"""
import os
import sqlite3
import feedparser
import requests
import json
import logging
import re
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional
from functools import lru_cache
import numpy as np

# Set custom cache directory to avoid permission issues
os.environ.setdefault('HF_HOME', os.path.join(os.getcwd(), '.hf_cache'))
os.environ.setdefault('TRANSFORMERS_CACHE', os.path.join(os.getcwd(), '.hf_cache'))

# Core imports
try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
    USE_SENTENCE_TRANSFORMERS = True
    USE_CROSS_ENCODER = True
except ImportError:
    USE_SENTENCE_TRANSFORMERS = False
    USE_CROSS_ENCODER = False
    raise ImportError("sentence-transformers is required")

# FlagEmbedding
try:
    from FlagEmbedding import FlagModel
    USE_FLAG_EMBEDDING = True
except ImportError:
    USE_FLAG_EMBEDDING = False

# NEW: BM25 for hybrid search
try:
    from rank_bm25 import BM25Okapi
    USE_BM25 = True
except ImportError:
    USE_BM25 = False
    print("Warning: rank-bm25 not installed. Hybrid search disabled.")

# NEW: FAISS for fast vector search
try:
    import faiss
    USE_FAISS = True
except ImportError:
    USE_FAISS = False
    print("Warning: faiss-cpu not installed. Using SQLite for search.")

# NEW: Better text splitting
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    USE_LANGCHAIN_SPLITTER = True
except ImportError:
    USE_LANGCHAIN_SPLITTER = False
    print("Warning: langchain-text-splitters not installed. Using basic splitter.")

# NEW: Chinese word segmentation and TF-IDF extraction
try:
    import jieba
    import jieba.posseg as pseg
    import jieba.analyse
    USE_JIEBA = True
except ImportError:
    USE_JIEBA = False
    print("Warning: jieba not installed. Keyword extraction disabled.")

# Load prompts
from app.prompts import load_prompt

# Add common domain words to jieba
if USE_JIEBA:
    jieba.add_word('馬拉松')
    jieba.add_word('马拉松')
    jieba.add_word('李家超')
    jieba.add_word('人工智能')

logger = logging.getLogger(__name__)

# Database setup
DB_PATH = os.getenv('RAG_DB_PATH', './rag_database.db')
EMBEDDING_DIM = 1024  # BAAI/bge-m3

class RAGSystem:
    def __init__(self, db_path: str = DB_PATH):
        """Initialize RAG system with enhanced capabilities"""
        self.db_path = db_path
        self.init_database()
        self.init_embedding_model()
        
        # NEW: FAISS index for fast vector search
        self.faiss_index = None
        self.id_to_article_map = {}
        if USE_FAISS:
            self._init_faiss_index()
        
        # NEW: Better text splitter
        if USE_LANGCHAIN_SPLITTER:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=300,
                chunk_overlap=50,
                separators=["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""],
                length_function=len
            )
        
        # Cache for search results
        self._search_cache = {}
        self._cache_max_size = 100
        
        logger.info("✓ Enhanced RAG system initialized")
    
    def init_database(self):
        """Initialize SQLite database with enriched metadata columns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Parent Articles table with ENRICHED keys
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                link TEXT UNIQUE,
                pub_date TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ENSURE NEW COLUMNS EXIST (Manual Migration)
        columns = [
            ("summary", "TEXT"),
            ("entities", "TEXT"),
            ("keywords", "TEXT"),
            ("category", "TEXT")
        ]
        
        cursor.execute("PRAGMA table_info(articles)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        for col_name, col_type in columns:
            if col_name not in existing_cols:
                logger.info(f"Adding missing column: {col_name}")
                cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")
        
        # Small-to-Big: Chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER,
                content TEXT NOT NULL,
                embedding BLOB,
                FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pub_date ON articles(pub_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON articles(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunk_article ON chunks(article_id)')
        
        conn.commit()
        conn.close()
        logger.info(f"Database enriched at {self.db_path}")
    
    def init_embedding_model(self):
        """Initialize embedding model for Chinese text"""
        model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        
        if model_name == 'BAAI/bge-m3' or 'bge-m3' in model_name.lower():
            if USE_FLAG_EMBEDDING:
                self._init_flag_embedding()
            else:
                self._init_sentence_transformer()
        else:
            self._init_sentence_transformer()
        
        use_rerank = os.getenv('RAG_USE_RERANK', 'true').lower() == 'true'
        if use_rerank:
            self._init_reranker()
        else:
            self.use_reranker = False
    
    def _init_flag_embedding(self):
        try:
            self.embedding_model = FlagModel('BAAI/bge-m3', use_fp16=False)
            self.use_flag_embedding = True
            logger.info("✓ Loaded: BAAI/bge-m3")
        except Exception as e:
            self._init_sentence_transformer()
    
    def _init_sentence_transformer(self):
        model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        try:
            self.embedding_model = SentenceTransformer(model_name)
            self.use_flag_embedding = False
            logger.info(f"✓ Loaded: {model_name}")
        except Exception as e:
            self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.use_flag_embedding = False
    
    def _init_reranker(self):
        if USE_CROSS_ENCODER:
            try:
                reranker_model = os.getenv('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
                self.reranker = CrossEncoder(reranker_model, max_length=128)
                self.use_reranker = True
                logger.info("✓ Reranker initialized")
            except:
                self.use_reranker = False
    
    def _init_faiss_index(self):
        """NEW: Initialize FAISS index from existing embeddings with disk persistence"""
        faiss_cache_path = os.path.join(os.path.dirname(self.db_path), "faiss_index.bin")
        faiss_map_path = os.path.join(os.path.dirname(self.db_path), "faiss_map.pkl")
        
        try:
            # Try loading from cache first
            if os.path.exists(faiss_cache_path) and os.path.exists(faiss_map_path):
                try:
                    import pickle
                    self.faiss_index = faiss.read_index(faiss_cache_path)
                    with open(faiss_map_path, 'rb') as f:
                        self.id_to_article_map = pickle.load(f)
                    logger.info(f"✓ FAISS index loaded from cache with {self.faiss_index.ntotal} vectors")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load FAISS cache: {e}, rebuilding...")
            
            # Build from scratch
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT article_id, embedding FROM chunks LIMIT 1')
            sample = cursor.fetchone()
            
            if sample:
                # Load all embeddings into FAISS
                cursor.execute('SELECT id, article_id, embedding FROM chunks')
                embeddings = []
                chunk_ids = []
                
                for chunk_id, article_id, emb_blob in cursor.fetchall():
                    emb = np.frombuffer(emb_blob, dtype=np.float32)
                    embeddings.append(emb)
                    chunk_ids.append((chunk_id, article_id))
                
                if embeddings:
                    embeddings_matrix = np.vstack(embeddings).astype('float32')
                    
                    # Normalize for cosine similarity
                    faiss.normalize_L2(embeddings_matrix)
                    
                    # Create index (use IVF for large datasets)
                    dim = embeddings_matrix.shape[1]
                    if len(embeddings) > 1000:
                        # Use IVF index for faster search with large datasets
                        nlist = min(100, int(np.sqrt(len(embeddings))))
                        quantizer = faiss.IndexFlatIP(dim)
                        self.faiss_index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
                        self.faiss_index.train(embeddings_matrix)
                        self.faiss_index.add(embeddings_matrix)
                        self.faiss_index.nprobe = 10  # Search 10 clusters
                        logger.info(f"✓ FAISS IVF index built with {len(embeddings)} vectors ({nlist} clusters)")
                    else:
                        # Use flat index for small datasets
                        self.faiss_index = faiss.IndexFlatIP(dim)
                        self.faiss_index.add(embeddings_matrix)
                        logger.info(f"✓ FAISS flat index built with {len(embeddings)} vectors")
                    
                    self.id_to_article_map = {i: (chunk_ids[i][0], chunk_ids[i][1]) for i in range(len(chunk_ids))}
                    
                    # Save to disk
                    try:
                        import pickle
                        faiss.write_index(self.faiss_index, faiss_cache_path)
                        with open(faiss_map_path, 'wb') as f:
                            pickle.dump(self.id_to_article_map, f)
                        logger.info(f"✓ FAISS index cached to disk")
                    except Exception as e:
                        logger.warning(f"Failed to cache FAISS index: {e}")
            
            conn.close()
        except Exception as e:
            logger.warning(f"FAISS initialization failed: {e}")
            self.faiss_index = None
    
    def get_embedding(self, text: str, batch: bool = False) -> np.ndarray:
        """Get embedding for text (supports batching)"""
        if isinstance(text, list):
            # Batch mode
            texts = [t[:1000] if any('\u4e00' <= c <= '\u9fff' for c in t) else t[:1500] for t in text]
            if hasattr(self, 'use_flag_embedding') and self.use_flag_embedding:
                results = [self.embedding_model.encode(t) for t in texts]
                embeddings = [r.get('dense_vec', r.get('dense', r)) if isinstance(r, dict) else r for r in results]
                return np.array([np.array(e).flatten() for e in embeddings])
            else:
                embeddings = self.embedding_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, 
                                                        show_progress_bar=False, batch_size=32, device='cpu')
                return embeddings
        else:
            # Single text mode
            max_chars = 1000 if any('\u4e00' <= c <= '\u9fff' for c in text) else 1500
            text = text[:max_chars]
            
            if hasattr(self, 'use_flag_embedding') and self.use_flag_embedding:
                result = self.embedding_model.encode(text)
                embedding = result.get('dense_vec', result.get('dense', result)) if isinstance(result, dict) else result
                return np.array(embedding).flatten()
            else:
                embedding = self.embedding_model.encode(text, convert_to_numpy=True, normalize_embeddings=True, 
                                                       show_progress_bar=False, batch_size=1, device='cpu')
                return embedding.flatten()

    def split_into_chunks(self, text: str, max_chunk_size: int = 300) -> List[str]:
        """NEW: Enhanced chunking with LangChain's RecursiveCharacterTextSplitter"""
        if USE_LANGCHAIN_SPLITTER:
            chunks = self.text_splitter.split_text(text)
            return [c.strip() for c in chunks if len(c.strip()) >= 5]
        else:
            # Fallback: Split by Chinese and English punctuation
            sentences = re.split(r'([。！？；.!?;])', text)
            chunks = []
            current_chunk = ""
            
            for i in range(0, len(sentences)-1, 2):
                s = sentences[i] + sentences[i+1] if i+1 < len(sentences) else sentences[i]
                if len(current_chunk) + len(s) < max_chunk_size:
                    current_chunk += s
                else:
                    if current_chunk: chunks.append(current_chunk)
                    current_chunk = s
            
            if current_chunk: chunks.append(current_chunk)
            return chunks

    def extract_entities(self, text: str) -> str:
        """NER: Extract People, Locations, Organizations"""
        if not USE_JIEBA: return ""
        try:
            words = pseg.cut(text[:1500])
            # nr: Person, ns: Location, nt: Org
            entities = [w.word for w in words if w.flag in ['nr', 'ns', 'nt']]
            return ", ".join(sorted(list(set([e for e in entities if len(e) > 1])))[:10])
        except: return ""

    def extract_keywords(self, text: str) -> str:
        """TF-IDF: Extract thematic keywords that define the topic"""
        if not USE_JIEBA: return ""
        try:
            # Using TF-IDF to find top 10 most "significant" words
            keywords = jieba.analyse.extract_tags(text, topK=10, withWeight=False)
            return ", ".join(keywords)
        except: return ""

    def classify_category(self, title: str, content: str) -> str:
        """NEW: LLM-based categorization for higher precision"""
        try:
            # Load from external prompt file
            template = load_prompt("classify_category.txt")
            if template:
                prompt = template.format(title=title, content=content[:300])
            else:
                # Fallback if file missing
                prompt = f"將此新聞分類為以下之一：Politics, Finance, Social, International, Sports, Tech, Health\n標題：{title}\n內容摘要：{content[:300]}\n分類："
            
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": "qwen2.5:0.5b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 10, "temperature": 0}
                },
                timeout=5
            )
            if response.status_code == 200:
                cat_raw = response.json().get('response', '').strip().replace(".", "").capitalize()
                # Clean up if the model outputs something like "Category: Tech"
                cat = re.sub(r'^.*:\s*', '', cat_raw)
                
                valid_cats = ["Politics", "Finance", "Social", "International", "Sports", "Tech", "Health"]
                for valid in valid_cats:
                    if valid.lower() in cat.lower():
                        return valid
        except Exception as e:
            logger.warning(f"LLM Categorization failed: {e}")
            
        # Fallback to keyword-based
        text = (title + " " + content).lower()
        categories = {
            "Finance": ["財經", "股市", "經濟", "銀行", "加息", "投資", "finance", "economy", "幣", "市場"],
            "Politics": ["政治", "政府", "特首", "法律", "選舉", "立法會", "politics", "government", "政策", "官員"],
            "Social": ["社會", "房屋", "交通", "罪案", "警察", "教育", "social", "society", "市民", "意外"],
            "International": ["國際", "美國", "中國", "日本", "戰爭", "外交", "international", "world", "俄羅斯", "歐盟"],
            "Sports": ["體育", "足球", "奧運", "籃球", "比賽", "sports", "football", "決賽", "歐聯"],
            "Tech": ["科技", "AI", "人工智能", "手機", "網絡", "technology", "tech", "晶片", "處理器", "發佈"],
            "Health": ["健康", "醫療", "病毒", "醫院", "疫情", "health", "medical", "藥物", "癌症", "疾病"]
        }
        for cat, keywords in categories.items():
            if any(kw in text for kw in keywords):
                return cat
        return "General"

    def generate_summary(self, title: str, content: str) -> str:
        """NEW: Generate a 1-sentence summary using small local model"""
        try:
            template = load_prompt("generate_summary.txt")
            if template:
                prompt = template.format(title=title, content=content[:500])
            else:
                prompt = f"請用一句話總結以下新聞：\n標題：{title}\n內容：{content[:500]}\n總結："
            
            # Use environment variable for Ollama URL, default to localhost for host-run scripts
            ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": "qwen2.5:0.5b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 100, "temperature": 0}
                },
                timeout=10
            )
            if response.status_code == 200:
                summary = response.json().get('response', '').strip()
                return summary
        except:
            pass
        return title # Fallback to title if LLM fails

    def store_article(self, article: Dict) -> bool:
        """NEW: Store article with ENRICHED metadata and SEMANTIC DEDUPLICATION"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Exact Link Check
            cursor.execute('SELECT id FROM articles WHERE link = ?', (article['link'],))
            if cursor.fetchone():
                conn.close()
                return False
            
            # 2. Semantic Deduplication (Title Similarity)
            # Check if an article with a very similar title already exists from today
            today_prefix = datetime.now().strftime("%a, %d %b %Y")
            cursor.execute('SELECT id, title FROM articles WHERE pub_date LIKE ?', (f'%{today_prefix}%',))
            existing_today = cursor.fetchall()
            
            for _, existing_title in existing_today:
                # Use a simple fuzzy match for titles
                if article['title'] in existing_title or existing_title in article['title']:
                    logger.info(f"🚫 Skipping duplicate news (semantic match): {article['title'][:30]}")
                    conn.close()
                    return False
            
            # 3. ENRICH the article
            logger.info(f"✨ Enriching: {article['title'][:30]}...")
            summary = self.generate_summary(article['title'], article['content'])
            text_for_analysis = article['title'] + " " + article['content']
            entities = self.extract_entities(text_for_analysis)
            keywords = self.extract_keywords(text_for_analysis)
            category = self.classify_category(article['title'], article['content'])
            
            # 2. Store Parent Article with new keys
            # Use INSERT OR IGNORE to handle race conditions gracefully
            cursor.execute('''
                INSERT OR IGNORE INTO articles (title, content, summary, entities, keywords, category, link, pub_date, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['title'], 
                article['content'], 
                summary, 
                entities,
                keywords,
                category, 
                article['link'], 
                article['pub_date'], 
                article['source']
            ))
            
            # Check if it was actually inserted
            if cursor.rowcount == 0:
                conn.close()
                return False
                
            article_id = cursor.lastrowid
            
            # 3. Create Chunks (Small-to-Big)
            # We also store the summary as a searchable chunk
            chunks = [article['title'], summary] + self.split_into_chunks(article['content'])
            chunks = [c for c in chunks if len(c.strip()) >= 5]
            
            # 4. BATCH Generate Embeddings
            if len(chunks) > 0:
                embeddings = self.get_embedding(chunks)
                for chunk_content, embedding in zip(chunks, embeddings):
                    cursor.execute('INSERT INTO chunks (article_id, content, embedding) VALUES (?, ?, ?)',
                                 (article_id, chunk_content, embedding.tobytes()))
            
            conn.commit()
            conn.close()
            
            if USE_FAISS and self.faiss_index is not None:
                self._rebuild_faiss_index()
            
            logger.info(f"✅ Enriched & Stored: [{category}] {article['title'][:40]}")
            return True
        except Exception as e:
            logger.error(f"Store enrichment error: {e}")
            conn.close()
            return False

    def _rebuild_faiss_index(self):
        """Rebuild FAISS index after new articles are added"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, article_id, embedding FROM chunks')
            
            embeddings = []
            chunk_ids = []
            
            for chunk_id, article_id, emb_blob in cursor.fetchall():
                emb = np.frombuffer(emb_blob, dtype=np.float32)
                embeddings.append(emb)
                chunk_ids.append((chunk_id, article_id))
            
            conn.close()
            
            if embeddings:
                embeddings_matrix = np.vstack(embeddings).astype('float32')
                faiss.normalize_L2(embeddings_matrix)
                
                self.faiss_index = faiss.IndexFlatIP(embeddings_matrix.shape[1])
                self.faiss_index.add(embeddings_matrix)
                self.id_to_article_map = {i: (chunk_ids[i][0], chunk_ids[i][1]) for i in range(len(chunk_ids))}
                
                logger.info(f"✓ FAISS index rebuilt with {len(embeddings)} vectors")
        except Exception as e:
            logger.error(f"FAISS rebuild error: {e}")

    def fetch_rss_feed(self, rss_url: str) -> List[Dict]:
        try:
            feed = feedparser.parse(rss_url)
            articles = []
            for entry in feed.entries:
                articles.append({
                    'title': entry.get('title', ''),
                    'content': entry.get('description', entry.get('summary', '')),
                    'link': entry.get('link', ''),
                    'pub_date': entry.get('published', entry.get('updated', '')),
                    'source': rss_url
                })
            return articles
        except Exception as e:
            logger.error(f"RSS error: {e}")
            return []

    def update_rss_feed(self, rss_url: str) -> int:
        articles = self.fetch_rss_feed(rss_url)
        stored_count = 0
        for article in articles:
            if self.store_article(article): stored_count += 1
        return stored_count

    def get_related_articles(self, article_id: int, limit: int = 5) -> List[Dict]:
        """Find related articles using Keyword Overlap (Jaccard Similarity)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Get current article metadata
            cursor.execute('SELECT entities, keywords, category FROM articles WHERE id = ?', (article_id,))
            row = cursor.fetchone()
            if not row: return []
            
            ent_str, kw_str, category = row
            target_tags = set([t.strip() for t in (ent_str + "," + kw_str).split(',') if t.strip()])
            
            # 2. Find candidates (same category or sharing some tags)
            cursor.execute('''
                SELECT id, title, entities, keywords, category, pub_date 
                FROM articles 
                WHERE id != ? AND (category = ? OR entities LIKE ? OR keywords LIKE ?)
                ORDER BY created_at DESC LIMIT 100
            ''', (article_id, category, f'%{ent_str[:10]}%', f'%{kw_str[:10]}%'))
            
            candidates = []
            for r_id, r_title, r_ent, r_kw, r_cat, r_date in cursor.fetchall():
                r_tags = set([t.strip() for t in (r_ent + "," + r_kw).split(',') if t.strip()])
                
                # Jaccard Similarity Calculation
                intersection = target_tags.intersection(r_tags)
                union = target_tags.union(r_tags)
                score = len(intersection) / len(union) if union else 0
                
                # Bonus for same category
                if r_cat == category: score += 0.1
                
                candidates.append({
                    'id': r_id, 'title': r_title, 'score': score, 
                    'category': r_cat, 'pub_date': r_date,
                    'reason': f'Shared: {", ".join(list(intersection)[:3])}' if intersection else 'Thematic match'
                })
            
            # Sort by relationship score
            return sorted(candidates, key=lambda x: x['score'], reverse=True)[:limit]
        finally:
            conn.close()

    def _calculate_temporal_weight(self, pub_date_str: str) -> float:
        """Calculate weight boost for recent articles (Aggressive Recency Decay)"""
        if not pub_date_str: return 0.7
        
        try:
            # Parse different date formats
            try:
                dt = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
            except:
                try:
                    dt = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                except:
                    # Fallback for other formats
                    return 0.7
            
            now = datetime.now(timezone.utc)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            
            diff = now - dt
            age_hours = diff.total_seconds() / 3600
            
            # AGGRESSIVE BOOST:
            # < 12 hours: 1.5x boost
            # < 24 hours: 1.3x boost
            # < 3 days: 1.1x boost
            # > 7 days: 0.8x penalty
            # > 30 days: 0.5x penalty
            
            if age_hours < 12:
                return 1.5
            elif age_hours < 24:
                return 1.3
            elif age_hours < 72: # 3 days
                return 1.1
            elif age_hours < 168: # 1 week
                return 1.0
            elif age_hours < 720: # 1 month
                return 0.8
            else:
                return 0.5
        except:
            return 0.7

    def _get_cache_key(self, query: str, top_k: int) -> str:
        """Generate cache key for query"""
        return hashlib.md5(f"{query}_{top_k}".encode()).hexdigest()

    def search_articles(self, query: str, top_k: int = 3, min_similarity: float = 0.25, use_rerank: bool = True, category: str = None) -> List[Dict]:
        """NEW: Enhanced search with Category filtering and hybrid scoring"""
        
        # Check cache first
        cache_key = self._get_cache_key(f"{query}_{category}", top_k)
        if cache_key in self._search_cache:
            logger.info(f"✓ Cache hit for query: {query[:30]}")
            return self._search_cache[cache_key]
        
        # Route to appropriate search method
        if USE_FAISS and self.faiss_index is not None:
            results = self._search_with_faiss(query, top_k, min_similarity, category)
        else:
            results = self._search_with_sqlite(query, top_k, min_similarity, category)
        
        # NEW: Apply BM25 hybrid scoring
        if USE_BM25 and results:
            results = self._apply_bm25_hybrid(query, results)
        
        # NEW: Entity-based boosting
        if USE_JIEBA and results:
            results = self._apply_entity_boost(query, results)
        
        # Apply reranking
        if use_rerank and self.use_reranker and results:
            final_results = self.rerank_results(query, results, top_k)
        else:
            final_results = sorted(results, key=lambda x: x['similarity'], reverse=True)[:top_k]
        
        # Cache results (avoid caching empty results to prevent sticky false negatives)
        if final_results:
            if len(self._search_cache) >= self._cache_max_size:
                # Remove oldest entry
                self._search_cache.pop(next(iter(self._search_cache)))
            self._search_cache[cache_key] = final_results
        
        return final_results

    def _search_with_faiss(self, query: str, top_k: int, min_similarity: float, category: str = None) -> List[Dict]:
        """NEW: Fast vector search with Category filtering"""
        try:
            query_embedding = self.get_embedding(query).astype('float32')
            faiss.normalize_L2(query_embedding.reshape(1, -1))
            
            # Search FAISS index (get more candidates to filter by category)
            k_candidates = 50 if category else 20
            k = min(k_candidates, self.faiss_index.ntotal)
            distances, indices = self.faiss_index.search(query_embedding.reshape(1, -1), k)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            results = []
            seen_articles = set()
            
            for idx, similarity in zip(indices[0], distances[0]):
                if idx == -1 or similarity < min_similarity:
                    continue
                
                chunk_id, article_id = self.id_to_article_map[idx]
                if article_id in seen_articles: continue
                
                # Fetch with category filter
                if category:
                    cursor.execute('''
                        SELECT title, content, summary, entities, keywords, category, link, pub_date, source
                        FROM articles WHERE id = ? AND category = ?
                    ''', (article_id, category))
                else:
                    cursor.execute('''
                        SELECT title, content, summary, entities, keywords, category, link, pub_date, source
                        FROM articles WHERE id = ?
                    ''', (article_id,))
                
                row = cursor.fetchone()
                if row:
                    seen_articles.add(article_id)
                    title, content, summary, entities, keywords, cat, link, pub_date, source = row
                    
                    time_weight = self._calculate_temporal_weight(pub_date)
                    weighted_score = float(similarity) * (0.7 + (0.3 * time_weight))
                    
                    results.append({
                        'id': article_id, 'title': title, 'content': content, 'summary': summary, 
                        'entities': entities, 'keywords': keywords, 'category': cat, 'link': link, 
                        'pub_date': pub_date, 'source': source, 'similarity': weighted_score
                    })
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"FAISS search error: {e}")
            return self._search_with_sqlite(query, top_k, min_similarity, category)

    def _search_with_sqlite(self, query: str, top_k: int, min_similarity: float, category: str = None) -> List[Dict]:
        """Fallback: SQLite-based search with Category filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            query_embedding = self.get_embedding(query)
            
            sql = '''
                SELECT c.article_id, c.content, c.embedding, a.title, a.content, a.summary, a.entities, a.keywords, a.category, a.link, a.pub_date, a.source
                FROM chunks c
                JOIN articles a ON c.article_id = a.id
                WHERE a.id IN (SELECT id FROM articles ORDER BY created_at DESC LIMIT 200)
            '''
            params = []
            if category:
                sql += " AND a.category = ?"
                params.append(category)
                
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            if not rows: return []

            results = []
            for article_id, chunk_text, emb_blob, title, full_content, summary, entities, kw, cat, link, pub_date, source in rows:
                if emb_blob is None:
                    continue
                try:
                    chunk_emb = np.frombuffer(emb_blob, dtype=np.float32)
                except Exception:
                    continue
                    
                if len(chunk_emb) != len(query_embedding): continue
                
                similarity = np.dot(chunk_emb, query_embedding) / (np.linalg.norm(chunk_emb) * np.linalg.norm(query_embedding))
                time_weight = self._calculate_temporal_weight(pub_date)
                weighted_score = similarity * (0.7 + (0.3 * time_weight))
                
                if weighted_score >= min_similarity:
                    results.append({
                        'id': article_id, 'title': title, 'content': full_content, 'summary': summary,
                        'matched_chunk': chunk_text, 'entities': entities, 'keywords': kw, 'category': cat,
                        'link': link, 'pub_date': pub_date, 'source': source, 'similarity': float(weighted_score)
                    })

            unique_results = {}
            for res in results:
                if res['id'] not in unique_results or res['similarity'] > unique_results[res['id']]['similarity']:
                    unique_results[res['id']] = res
            
            return sorted(unique_results.values(), key=lambda x: x['similarity'], reverse=True)
        finally:
            conn.close()

    def _apply_bm25_hybrid(self, query: str, results: List[Dict]) -> List[Dict]:
        """NEW: Apply BM25 keyword scoring and combine with vector scores"""
        try:
            # Build corpus from results
            corpus = [r['content'] for r in results]
            
            # Use jieba for tokenization if available and text is Chinese
            def tokenize(text):
                if USE_JIEBA:
                    return list(jieba.cut(text))
                return text.split()
            
            tokenized_corpus = [tokenize(doc) for doc in corpus]
            
            # BM25 scoring
            bm25 = BM25Okapi(tokenized_corpus)
            bm25_scores = bm25.get_scores(tokenize(query))
            
            # Normalize BM25 scores to [0, 1]
            max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
            normalized_bm25 = [s / max_bm25 for s in bm25_scores]
            
            # Hybrid score: 60% vector + 40% BM25
            for i, result in enumerate(results):
                original_sim = result['similarity']
                bm25_sim = normalized_bm25[i]
                result['similarity'] = 0.6 * original_sim + 0.4 * bm25_sim
                result['bm25_score'] = bm25_sim
            
            logger.info(f"✓ BM25 hybrid scoring applied")
            return results
            
        except Exception as e:
            logger.warning(f"BM25 hybrid failed: {e}")
            return results

    def _apply_entity_boost(self, query: str, results: List[Dict]) -> List[Dict]:
        """NEW: Boost results that contain all query entities"""
        try:
            entities_str = self.extract_entities(query)
            if not entities_str:
                return results
                
            query_entities = set([e.strip() for e in entities_str.split(',') if e.strip()])
            if not query_entities:
                return results
            
            for result in results:
                content_entities_str = self.extract_entities(result['title'] + " " + result['content'][:500])
                content_entities = set([e.strip() for e in content_entities_str.split(',') if e.strip()])
                
                overlap = len(query_entities & content_entities) / len(query_entities)
                
                # Boost by up to 30% if all entities match
                result['similarity'] *= (1 + overlap * 0.3)
                result['entity_overlap'] = overlap
            
            logger.info(f"✓ Entity boosting applied (query entities: {query_entities})")
            return results
            
        except Exception as e:
            logger.warning(f"Entity boosting failed: {e}")
            return results

    def rerank_results(self, query: str, results: List[Dict], top_k: int) -> List[Dict]:
        max_rerank = min(len(results), 10)
        candidates = results[:max_rerank]
        pairs = [[query, f"{c['title']}\n{c['content'][:200]}"] for c in candidates]
        
        scores = self.reranker.predict(pairs, show_progress_bar=False)
        for i, score in enumerate(scores):
            norm_score = (score + 10) / 20 if score > 1 else score
            candidates[i]['similarity'] = (candidates[i]['similarity'] * 0.4) + (norm_score * 0.6)
            
        return sorted(candidates, key=lambda x: x['similarity'], reverse=True)[:top_k]

    def get_article_count(self) -> int:
        conn = sqlite3.connect(self.db_path); c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM articles'); count = c.fetchone()[0]; conn.close()
        return count

    def list_articles(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        conn = sqlite3.connect(self.db_path); c = conn.cursor()
        c.execute('SELECT id, title, content, summary, entities, keywords, category, link, pub_date, source, created_at FROM articles ORDER BY created_at DESC LIMIT ? OFFSET ?', (limit, offset))
        articles = [{'id': r[0], 'title': r[1], 'content': r[2][:200], 'summary': r[3], 'entities': r[4], 'keywords': r[5], 'category': r[6], 'link': r[7], 'pub_date': r[8], 'source': r[9]} for r in c.fetchall()]
        conn.close(); return articles

    def get_article_detail(self, article_id: int) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path); c = conn.cursor()
        c.execute('SELECT id, title, content, summary, entities, keywords, category, link, pub_date, source, created_at FROM articles WHERE id = ?', (article_id,))
        row = c.fetchone(); conn.close()
        if row:
            return {'id': row[0], 'title': row[1], 'content': row[2], 'summary': row[3], 'entities': row[4], 'keywords': row[5], 'category': row[6], 'link': row[7], 'pub_date': row[8], 'source': row[9]}
        return None

    def delete_article(self, article_id: int) -> bool:
        conn = sqlite3.connect(self.db_path); c = conn.cursor()
        c.execute('DELETE FROM articles WHERE id = ?', (article_id,))
        conn.commit(); deleted = c.rowcount > 0; conn.close()
        
        # Rebuild FAISS if enabled
        if deleted and USE_FAISS and self.faiss_index is not None:
            self._rebuild_faiss_index()
        
        return deleted

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    rag = RAGSystem()
    print(f"Count: {rag.get_article_count()}")

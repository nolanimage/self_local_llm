import sqlite3
import os
import sys
import logging
import requests
import jieba.analyse
import jieba.posseg as pseg

# Database path
DB_PATH = os.getenv('RAG_DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rag_database.db'))
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_entities(text):
    try:
        words = pseg.cut(text[:1500])
        entities = [w.word for w in words if w.flag in ['nr', 'ns', 'nt']]
        return ", ".join(sorted(list(set([e for e in entities if len(e) > 1])))[:10])
    except: return ""

def extract_keywords(text):
    try:
        keywords = jieba.analyse.extract_tags(text, topK=10, withWeight=False)
        return ", ".join(keywords)
    except: return ""

def generate_summary(title, content):
    try:
        prompt = f"請用一句話總結以下新聞：\n標題：{title}\n內容：{content[:500]}\n總結："
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "qwen2.5:0.5b", "prompt": prompt, "stream": False, "options": {"num_predict": 100, "temperature": 0}},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
    except: pass
    return title

def classify_category(title, content):
    try:
        prompt = f"將此新聞分類為以下之一：Politics, Finance, Social, International, Sports, Tech, Health\n標題：{title}\n內容摘要：{content[:300]}\n分類："
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "qwen2.5:0.5b", "prompt": prompt, "stream": False, "options": {"num_predict": 10, "temperature": 0}},
            timeout=5
        )
        if response.status_code == 200:
            cat = response.json().get('response', '').strip().replace(".", "").capitalize()
            valid_cats = ["Politics", "Finance", "Social", "International", "Sports", "Tech", "Health"]
            for v in valid_cats:
                if v.lower() in cat.lower(): return v
    except: pass
    return "General"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, title, content FROM articles WHERE keywords IS NULL OR summary IS NULL')
    articles = cursor.fetchall()
    logger.info(f"Found {len(articles)} articles to enrich.")
    
    for i, (art_id, title, content) in enumerate(articles):
        logger.info(f"[{i+1}/{len(articles)}] Enriching: {title[:30]}...")
        text = title + " " + content
        
        entities = extract_entities(text)
        keywords = extract_keywords(text)
        summary = generate_summary(title, content)
        category = classify_category(title, content)
        
        cursor.execute('''
            UPDATE articles 
            SET entities = ?, keywords = ?, summary = ?, category = ? 
            WHERE id = ?
        ''', (entities, keywords, summary, category, art_id))
        
        if (i+1) % 5 == 0:
            conn.commit()
            logger.info("Committed batch.")
            
    conn.commit()
    conn.close()
    logger.info("✅ Enrichment complete!")

if __name__ == "__main__":
    migrate()

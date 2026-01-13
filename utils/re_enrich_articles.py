import os
import sqlite3
import logging
from app.rag_system import RAGSystem

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def re_enrich():
    rag = RAGSystem()
    conn = sqlite3.connect(rag.db_path)
    cursor = conn.cursor()
    
    # Find articles with missing metadata
    cursor.execute('''
        SELECT id, title, content 
        FROM articles 
        WHERE keywords IS NULL OR keywords = '' OR entities IS NULL OR entities = '' OR category = 'General'
    ''')
    articles = cursor.fetchall()
    
    logger.info(f"Found {len(articles)} articles needing re-enrichment")
    
    count = 0
    for art_id, title, content in articles:
        try:
            text_for_analysis = title + " " + content
            
            # Extract
            logger.info(f"[{count+1}/{len(articles)}] Enriching: {title[:40]}...")
            entities = rag.extract_entities(text_for_analysis)
            keywords = rag.extract_keywords(text_for_analysis)
            category = rag.classify_category(title, content)
            summary = rag.generate_summary(title, content)
            
            # Update
            cursor.execute('''
                UPDATE articles 
                SET entities = ?, keywords = ?, category = ?, summary = ?
                WHERE id = ?
            ''', (entities, keywords, category, summary, art_id))
            
            count += 1
            if count % 10 == 0:
                conn.commit()
                logger.info(f"Progress: {count} articles updated")
                
        except Exception as e:
            logger.error(f"Failed to enrich article {art_id}: {e}")
            
    conn.commit()
    conn.close()
    logger.info(f"Done! Updated {count} articles.")

if __name__ == "__main__":
    re_enrich()

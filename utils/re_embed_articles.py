import sqlite3
import os
import sys
import logging

# Set path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.rag_system import RAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_existing_articles():
    rag = RAGSystem()
    conn = sqlite3.connect(rag.db_path)
    cursor = conn.cursor()
    
    # 1. Find articles that need enrichment
    # We look for those with missing summary, default category, or missing entities
    cursor.execute('''
        SELECT id, title, content, category, summary, entities, keywords
        FROM articles 
        WHERE summary IS NULL OR category = 'General' OR entities IS NULL OR keywords IS NULL
    ''')
    
    articles = cursor.fetchall()
    logger.info(f"Found {len(articles)} articles needing enrichment.")
    
    count = 0
    for art_id, title, content, old_cat, old_summary, old_entities, old_keywords in articles:
        count += 1
        logger.info(f"[{count}/{len(articles)}] Enriching: {title[:40]}...")
        
        # Extract new data
        new_summary = rag.generate_summary(title, content) if not old_summary else old_summary
        new_entities = rag.extract_entities(title + " " + content) if not old_entities else old_entities
        new_keywords = rag.extract_keywords(title + " " + content) if not old_keywords else old_keywords
        new_cat = rag.classify_category(title, content)
        
        # Update database
        cursor.execute('''
            UPDATE articles 
            SET summary = ?, entities = ?, keywords = ?, category = ? 
            WHERE id = ?
        ''', (new_summary, new_entities, new_keywords, new_cat, art_id))
        
        if count % 10 == 0:
            conn.commit()
            logger.info(f"Progress: {count} committed.")
            
    conn.commit()
    conn.close()
    logger.info("✅ Migration complete!")

if __name__ == "__main__":
    migrate_existing_articles()

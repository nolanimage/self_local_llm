#!/usr/bin/env python3
"""
Script to update RSS feeds and store articles in RAG database
"""
import os
import sys
import logging
from app.rag_system import RAGSystem

# Default RSS feeds - RTHK (Radio Television Hong Kong)
DEFAULT_RSS_FEEDS = [
    "https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_clocal.xml",  # Local news
    "https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_greaterchina.xml",  # Greater China news
    "https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_cinternational.xml",  # International news
    "https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_cfinance.xml",  # Finance news
    "https://rthk9.rthk.hk/rthk/news/rss/c_expressnews_csport.xml",  # Sports news
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate(rag):
    """Enrich existing articles with missing metadata (Category, Entities, Summary)"""
    import sqlite3
    logger.info("Starting database migration/enrichment...")
    conn = sqlite3.connect(rag.db_path)
    cursor = conn.cursor()
    
    # Check for articles missing enriched metadata
    cursor.execute('''
        SELECT id, title, content, category, summary, entities, keywords 
        FROM articles 
        WHERE summary IS NULL OR category = 'General' OR entities IS NULL OR keywords IS NULL
    ''')
    
    articles = cursor.fetchall()
    logger.info(f"Found {len(articles)} articles needing enrichment.")
    
    count = 0
    for art_id, title, content, old_cat, old_summary, old_entities, old_kw in articles:
        count += 1
        logger.info(f"[{count}/{len(articles)}] Enriching: {title[:40]}...")
        
        try:
            # Generate missing fields
            new_summary = rag.generate_summary(title, content) if not old_summary else old_summary
            new_entities = rag.extract_entities(title + " " + content) if not old_entities else old_entities
            new_kw = rag.extract_keywords(title + " " + content) if not old_kw else old_kw
            new_cat = rag.classify_category(title, content)
            
            cursor.execute('''
                UPDATE articles 
                SET summary = ?, entities = ?, keywords = ?, category = ? 
                WHERE id = ?
            ''', (new_summary, new_entities, new_kw, new_cat, art_id))
            
            if count % 10 == 0:
                conn.commit()
                logger.info(f"  Committed {count} updates...")
        except Exception as e:
            logger.error(f"  Error enriching article {art_id}: {e}")
            
    conn.commit()
    conn.close()
    logger.info("✅ Migration complete!")

def main():
    """Update RSS feeds"""
    rag = RAGSystem()
    
    # Check if we should run migration
    if len(sys.argv) > 1 and sys.argv[1] == '--migrate':
        migrate(rag)
        return
    
    # Get RSS feeds from environment or use defaults
    rss_feeds = os.getenv('RSS_FEEDS', ','.join(DEFAULT_RSS_FEEDS)).split(',')
    rss_feeds = [feed.strip() for feed in rss_feeds if feed.strip()]
    
    logger.info(f"Updating {len(rss_feeds)} RSS feed(s)...")
    
    total_stored = 0
    for rss_url in rss_feeds:
        logger.info(f"Processing: {rss_url}")
        stored = rag.update_rss_feed(rss_url)
        total_stored += stored
        logger.info(f"  Stored {stored} new articles")
    
    total_articles = rag.get_article_count()
    logger.info(f"\n✓ Update complete!")
    logger.info(f"  New articles stored: {total_stored}")
    logger.info(f"  Total articles in database: {total_articles}")


if __name__ == '__main__':
    main()

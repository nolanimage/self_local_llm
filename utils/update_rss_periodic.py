#!/usr/bin/env python3
"""
Periodic RSS feed updater - runs continuously and updates feeds at intervals
"""
import os
import sys
import time
import logging
from app.rag_system import RAGSystem

# Update interval in seconds (default: 10 minutes = 600 seconds)
UPDATE_INTERVAL = int(os.getenv('RSS_UPDATE_INTERVAL', '600'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def update_feeds(rag):
    """Update all reliable RSS feeds directly"""
    total_stored = 0
    
    rss_feeds = os.getenv('RSS_FEEDS', '').split(',')
    rss_feeds = [feed.strip() for feed in rss_feeds if feed.strip()]
    
    if rss_feeds:
        logger.info(f"🔄 Processing {len(rss_feeds)} reliable news feeds...")
        for rss_url in rss_feeds:
            try:
                stored = rag.update_rss_feed(rss_url)
                total_stored += stored
                if stored > 0:
                    logger.info(f"  + {stored} new articles from {rss_url.split('/')[-1]}")
            except Exception as e:
                logger.error(f"Error updating {rss_url}: {e}")
    
    total_articles = rag.get_article_count()
    logger.info(f"✅ Update complete! Total articles in DB: {total_articles}")
    return total_stored


def main():
    """Run periodic RSS updates"""
    rag = RAGSystem()
    
    logger.info(f"Starting RSS updater (interval: {UPDATE_INTERVAL}s = {UPDATE_INTERVAL/60:.1f} minutes)")
    
    # Periodic updates
    while True:
        try:
            logger.info("Starting scheduled update...")
            update_feeds(rag)
            
            logger.info(f"Waiting {UPDATE_INTERVAL}s until next update...")
            time.sleep(UPDATE_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Stopping RSS updater...")
            break
        except Exception as e:
            logger.error(f"Error in update cycle: {e}", exc_info=True)
            logger.info(f"Retrying in {UPDATE_INTERVAL}s...")
            time.sleep(UPDATE_INTERVAL)


if __name__ == '__main__':
    main()

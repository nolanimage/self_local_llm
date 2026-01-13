"""
Trending Topics Tracker
Tracks popular search queries and displays trending topics
"""
import time
from collections import defaultdict, Counter
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class TrendingTopics:
    """Track and analyze trending search queries"""
    
    def __init__(self, window_hours: int = 24):
        self.window_seconds = window_hours * 3600
        # Store: [(query, timestamp), ...]
        self.queries: List[tuple] = []
        
    def add_query(self, query: str):
        """Record a search query"""
        current_time = time.time()
        self.queries.append((query.lower().strip(), current_time))
        
        # Clean old queries periodically
        if len(self.queries) > 1000:
            self._clean_old_queries()
    
    def _clean_old_queries(self):
        """Remove queries outside the time window"""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        self.queries = [(q, t) for q, t in self.queries if t > cutoff_time]
    
    def get_trending(self, limit: int = 10) -> List[Dict]:
        """
        Get trending topics
        
        Returns:
            List of {query, count, percentage}
        """
        self._clean_old_queries()
        
        if not self.queries:
            return []
        
        # Count query frequency
        query_counts = Counter(q for q, t in self.queries)
        total_queries = len(self.queries)
        
        # Get top queries
        trending = []
        for query, count in query_counts.most_common(limit):
            percentage = (count / total_queries) * 100
            trending.append({
                "query": query,
                "count": count,
                "percentage": round(percentage, 1)
            })
        
        logger.info(f"Trending topics: {len(trending)} queries from {total_queries} total")
        return trending
    
    def get_stats(self) -> Dict:
        """Get overall trending stats"""
        self._clean_old_queries()
        
        total_queries = len(self.queries)
        unique_queries = len(set(q for q, t in self.queries))
        
        # Calculate time range
        if self.queries:
            oldest = min(t for q, t in self.queries)
            newest = max(t for q, t in self.queries)
            time_range_hours = (newest - oldest) / 3600
        else:
            time_range_hours = 0
        
        return {
            "total_queries": total_queries,
            "unique_queries": unique_queries,
            "time_window_hours": self.window_seconds / 3600,
            "actual_time_range_hours": round(time_range_hours, 1)
        }

# Global trending tracker instance
trending_tracker = TrendingTopics(window_hours=24)

"""
Rate Limiter for API endpoints
Implements 50 questions per hour per user quota
"""
import time
from collections import defaultdict
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Simple in-memory rate limiter
    Tracks requests per user with sliding window
    """
    def __init__(self, max_requests: int = 50, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Store: user_id -> [(timestamp1, timestamp2, ...)]
        self.requests: Dict[str, list] = defaultdict(list)
        
    def is_allowed(self, user_id: str) -> Tuple[bool, int, int]:
        """
        Check if user is allowed to make a request
        
        Returns:
            (is_allowed, remaining_quota, reset_time_seconds)
        """
        current_time = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests outside the window
        cutoff_time = current_time - self.window_seconds
        user_requests[:] = [ts for ts in user_requests if ts > cutoff_time]
        
        # Check if under limit
        if len(user_requests) < self.max_requests:
            user_requests.append(current_time)
            remaining = self.max_requests - len(user_requests)
            
            # Calculate reset time (when oldest request expires)
            reset_time = 0
            if user_requests:
                oldest_request = min(user_requests)
                reset_time = int(oldest_request + self.window_seconds - current_time)
            
            logger.info(f"User {user_id}: Request allowed. Remaining: {remaining}/{self.max_requests}")
            return True, remaining, reset_time
        else:
            # Rate limited
            oldest_request = min(user_requests)
            reset_time = int(oldest_request + self.window_seconds - current_time)
            logger.warning(f"User {user_id}: Rate limited. Reset in {reset_time}s")
            return False, 0, reset_time
    
    def get_stats(self, user_id: str) -> Dict:
        """Get current usage stats for a user"""
        current_time = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests
        cutoff_time = current_time - self.window_seconds
        user_requests[:] = [ts for ts in user_requests if ts > cutoff_time]
        
        used = len(user_requests)
        remaining = self.max_requests - used
        
        reset_time = 0
        if user_requests:
            oldest_request = min(user_requests)
            reset_time = int(oldest_request + self.window_seconds - current_time)
        
        return {
            "limit": self.max_requests,
            "used": used,
            "remaining": remaining,
            "reset_in_seconds": reset_time,
            "window_hours": self.window_seconds / 3600
        }
    
    def reset_user(self, user_id: str):
        """Reset rate limit for a specific user (admin function)"""
        if user_id in self.requests:
            del self.requests[user_id]
            logger.info(f"Rate limit reset for user: {user_id}")

# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=50, window_seconds=3600)  # 50 per hour

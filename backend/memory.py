"""
Zero Me - Redis Memory Manager
Handles personal context storage and retrieval using Redis
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import redis
from loguru import logger

from parameters import MEMORY_CONFIG


class MemoryManager:
    """
    Manages personal context and conversation memory using Redis.
    
    Key structure:
    - zero_me:user:{user_id}:context - Hash of personal context items
    - zero_me:user:{user_id}:conversations - List of conversation summaries
    - zero_me:user:{user_id}:analytics - Hash of analytics data
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis connection."""
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.prefix = MEMORY_CONFIG["redis_key_prefix"]
        self.ttl_days = MEMORY_CONFIG["context_ttl_days"]
        self.max_items = MEMORY_CONFIG["max_context_items"]
        
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Memory features will be disabled.")
            self.client = None
    
    def _get_key(self, user_id: str, key_type: str) -> str:
        """Generate a Redis key."""
        return f"{self.prefix}user:{user_id}:{key_type}"
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self.client is not None
    
    # ============================================
    # PERSONAL CONTEXT OPERATIONS
    # ============================================
    
    def store_context(self, user_id: str, context_key: str, context_value: str, category: str = "general") -> bool:
        """
        Store a piece of personal context.
        
        Args:
            user_id: User identifier
            context_key: Key for the context (e.g., "preferred_name", "timezone")
            context_value: The context value
            category: Category of context (e.g., "preferences", "work", "schedule")
            
        Returns:
            True if stored successfully
        """
        if not self.client:
            return False
            
        try:
            key = self._get_key(user_id, "context")
            
            # Store with timestamp and category
            data = {
                "value": context_value,
                "category": category,
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            self.client.hset(key, context_key, json.dumps(data))
            self.client.expire(key, timedelta(days=self.ttl_days))
            
            logger.debug(f"Stored context for user {user_id}: {context_key} (category: {category})")
            return True
        except Exception as e:
            logger.error(f"Failed to store context: {e}")
            return False
    
    def retrieve_context(self, user_id: str, context_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve personal context.
        
        Args:
            user_id: User identifier
            context_key: Specific key to retrieve, or None for all context
            
        Returns:
            Context data or None
        """
        if not self.client:
            return None
            
        try:
            key = self._get_key(user_id, "context")
            
            if context_key:
                data = self.client.hget(key, context_key)
                return json.loads(data) if data else None
            else:
                all_data = self.client.hgetall(key)
                return {k: json.loads(v) for k, v in all_data.items()}
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return None
    
    def search_context(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Search context for matching items.
        
        Args:
            user_id: User identifier
            query: Search query
            
        Returns:
            List of matching context items
        """
        if not self.client:
            return []
            
        try:
            all_context = self.retrieve_context(user_id)
            if not all_context:
                return []
            
            query_lower = query.lower()
            results = []
            
            for key, data in all_context.items():
                if query_lower in key.lower() or query_lower in data.get("value", "").lower():
                    results.append({"key": key, **data})
            
            return results
        except Exception as e:
            logger.error(f"Failed to search context: {e}")
            return []
    
    def delete_context(self, user_id: str, context_key: str) -> bool:
        """Delete a specific context item."""
        if not self.client:
            return False
            
        try:
            key = self._get_key(user_id, "context")
            self.client.hdel(key, context_key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete context: {e}")
            return False
    
    # ============================================
    # CONVERSATION HISTORY OPERATIONS
    # ============================================
    
    def store_conversation_summary(
        self, 
        user_id: str, 
        summary: Optional[Dict[str, Any]] = None,
        topics: Optional[List[str]] = None,
        duration: int = 0,
    ) -> bool:
        """
        Store a conversation summary.
        
        Args:
            user_id: User identifier
            summary: Conversation summary dict, or will be built from other params
            topics: List of topics discussed
            duration: Duration in seconds
        """
        if not self.client:
            return False
            
        try:
            key = self._get_key(user_id, "conversations")
            
            # Build summary if not provided
            if summary is None:
                summary = {}
            
            # Add/update fields
            summary["timestamp"] = summary.get("timestamp", datetime.utcnow().isoformat())
            if topics:
                summary["topics"] = topics
            if duration:
                summary["duration_seconds"] = duration
            
            self.client.lpush(key, json.dumps(summary))
            self.client.ltrim(key, 0, self.max_items - 1)  # Keep only recent
            self.client.expire(key, timedelta(days=self.ttl_days))
            
            logger.debug(f"Stored conversation summary for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store conversation summary: {e}")
            return False
    
    async def store_conversation_summary_async(
        self, 
        user_id: str, 
        summary: Optional[str] = None,
        topics: Optional[List[str]] = None,
        duration: int = 0,
    ) -> bool:
        """Async version of store_conversation_summary."""
        # For now, just call the sync version
        # In a production app, use aioredis
        return self.store_conversation_summary(
            user_id, 
            {"summary": summary} if isinstance(summary, str) else summary,
            topics,
            duration
        )
    
    def get_recent_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation summaries."""
        if not self.client:
            return []
            
        try:
            key = self._get_key(user_id, "conversations")
            data = self.client.lrange(key, 0, limit - 1)
            return [json.loads(item) for item in data]
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}")
            return []
    
    # ============================================
    # ANALYTICS OPERATIONS
    # ============================================
    
    def increment_analytics(self, user_id: str, metric: str, amount: int = 1) -> bool:
        """Increment an analytics counter."""
        if not self.client:
            return False
            
        try:
            key = self._get_key(user_id, "analytics")
            self.client.hincrby(key, metric, amount)
            return True
        except Exception as e:
            logger.error(f"Failed to increment analytics: {e}")
            return False
    
    def get_analytics(self, user_id: str) -> Dict[str, int]:
        """Get all analytics for a user."""
        if not self.client:
            return {}
            
        try:
            key = self._get_key(user_id, "analytics")
            data = self.client.hgetall(key)
            return {k: int(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {}


# Global instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager

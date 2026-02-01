"""
Zero Me - Memory Tools
LangChain tools for Redis memory operations
"""

import os
from typing import Optional
from langchain.tools import tool
from loguru import logger

# Import from parent directory
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory import get_memory_manager
from analytics import get_analytics_manager


# Default user ID for single-user mode
# In multi-user mode, this would come from authentication
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "default_user")


@tool
def store_memory(context_key: str, context_value: str, user_id: Optional[str] = None) -> str:
    """
    Store a piece of personal context in memory.
    
    Use this to remember user preferences, frequently mentioned topics,
    or any context that should persist across conversations.
    
    Args:
        context_key: A descriptive key for the context (e.g., "preferred_name", "work_schedule", "favorite_color")
        context_value: The value to store
        user_id: Optional user identifier (uses default if not provided)
    
    Returns:
        Success or error message
    
    Examples:
        - store_memory("preferred_name", "Alex") -> Remembers user likes to be called Alex
        - store_memory("timezone", "America/New_York") -> Remembers user's timezone
        - store_memory("project_focus", "Building a mobile app") -> Remembers current project
    """
    memory = get_memory_manager()
    analytics = get_analytics_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        return "Memory storage is currently unavailable (Redis not connected)."
    
    success = memory.store_context(uid, context_key, context_value)
    
    # Log to analytics
    analytics.log_memory_operation("store", uid, context_key, success)
    
    if success:
        logger.info(f"Stored memory: {context_key} for user {uid}")
        return f"I'll remember that: {context_key} = {context_value}"
    else:
        return "Failed to store memory. Please try again."


@tool
def retrieve_memory(context_key: Optional[str] = None, user_id: Optional[str] = None) -> str:
    """
    Retrieve personal context from memory.
    
    Args:
        context_key: Specific key to retrieve, or None to get all stored context
        user_id: Optional user identifier
    
    Returns:
        Retrieved context or message if not found
    """
    memory = get_memory_manager()
    analytics = get_analytics_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        return "Memory storage is currently unavailable (Redis not connected)."
    
    result = memory.retrieve_context(uid, context_key)
    
    # Log to analytics
    analytics.log_memory_operation("retrieve", uid, context_key or "all", result is not None)
    
    if result is None:
        if context_key:
            return f"I don't have any memory stored for '{context_key}'."
        return "No memories stored yet."
    
    if context_key:
        return f"I remember: {context_key} = {result.get('value')}"
    else:
        # Format all memories
        if not result:
            return "No memories stored yet."
        
        memories = []
        for key, data in result.items():
            memories.append(f"- {key}: {data.get('value')}")
        
        return "Here's what I remember:\n" + "\n".join(memories)


@tool
def search_memory(query: str, user_id: Optional[str] = None) -> str:
    """
    Search through stored memories for matching context.
    
    Args:
        query: Search term to find in memory keys or values
        user_id: Optional user identifier
    
    Returns:
        Matching memories or message if none found
    """
    memory = get_memory_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        return "Memory storage is currently unavailable (Redis not connected)."
    
    results = memory.search_context(uid, query)
    
    if not results:
        return f"No memories found matching '{query}'."
    
    memories = []
    for item in results:
        memories.append(f"- {item.get('key')}: {item.get('value')}")
    
    return f"Found {len(results)} matching memories:\n" + "\n".join(memories)


@tool
def delete_memory(context_key: str, user_id: Optional[str] = None) -> str:
    """
    Delete a specific memory.
    
    Args:
        context_key: The key of the memory to delete
        user_id: Optional user identifier
    
    Returns:
        Success or error message
    """
    memory = get_memory_manager()
    analytics = get_analytics_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        return "Memory storage is currently unavailable (Redis not connected)."
    
    success = memory.delete_context(uid, context_key)
    
    # Log to analytics
    analytics.log_memory_operation("delete", uid, context_key, success)
    
    if success:
        return f"Deleted memory: {context_key}"
    else:
        return f"Failed to delete memory '{context_key}'. It may not exist."


@tool
def get_conversation_history(limit: int = 5, user_id: Optional[str] = None) -> str:
    """
    Get recent conversation summaries.
    
    Args:
        limit: Number of recent conversations to retrieve
        user_id: Optional user identifier
    
    Returns:
        Recent conversation summaries
    """
    memory = get_memory_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        return "Memory storage is currently unavailable (Redis not connected)."
    
    conversations = memory.get_recent_conversations(uid, limit)
    
    if not conversations:
        return "No conversation history found."
    
    summaries = []
    for i, conv in enumerate(conversations, 1):
        topic = conv.get("topic", "Unknown topic")
        timestamp = conv.get("timestamp", "Unknown time")
        questions = conv.get("questions_asked", 0)
        summaries.append(f"{i}. {topic} ({timestamp}) - {questions} questions asked")
    
    return f"Recent {len(conversations)} conversations:\n" + "\n".join(summaries)

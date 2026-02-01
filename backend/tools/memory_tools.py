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
from tools.logging_utils import log_tool_call, log_tool_result, log_memory_operation


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
    log_tool_call("store_memory", {"key": context_key, "value": context_value[:50] + "..." if len(context_value) > 50 else context_value})
    
    memory = get_memory_manager()
    analytics = get_analytics_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        result = "Memory storage is currently unavailable (Redis not connected)."
        log_tool_result("store_memory", result, success=False)
        return result
    
    success = memory.store_context(uid, context_key, context_value)
    
    # Log to analytics
    analytics.log_memory_operation("store", uid, context_key, success)
    
    if success:
        log_memory_operation("STORE", context_key, context_value)
        result = f"I'll remember that: {context_key} = {context_value}"
        log_tool_result("store_memory", result, success=True)
        return result
    else:
        result = "Failed to store memory. Please try again."
        log_tool_result("store_memory", result, success=False)
        return result


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
    log_tool_call("retrieve_memory", {"key": context_key or "ALL"})
    
    memory = get_memory_manager()
    analytics = get_analytics_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        result = "Memory storage is currently unavailable (Redis not connected)."
        log_tool_result("retrieve_memory", result, success=False)
        return result
    
    data = memory.retrieve_context(uid, context_key)
    
    # Log to analytics
    analytics.log_memory_operation("retrieve", uid, context_key or "all", data is not None)
    
    if data is None:
        if context_key:
            result = f"I don't have any memory stored for '{context_key}'."
        else:
            result = "No memories stored yet."
        log_tool_result("retrieve_memory", result, success=True)
        return result
    
    if context_key:
        log_memory_operation("RETRIEVE", context_key, data.get('value'))
        result = f"I remember: {context_key} = {data.get('value')}"
    else:
        # Format all memories
        if not data:
            result = "No memories stored yet."
        else:
            memories = []
            for key, val in data.items():
                memories.append(f"- {key}: {val.get('value')}")
            result = "Here's what I remember:\n" + "\n".join(memories)
    
    log_tool_result("retrieve_memory", result, success=True)
    return result


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
    log_tool_call("search_memory", {"query": query})
    
    memory = get_memory_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        result = "Memory storage is currently unavailable (Redis not connected)."
        log_tool_result("search_memory", result, success=False)
        return result
    
    results = memory.search_context(uid, query)
    
    if not results:
        result = f"No memories found matching '{query}'."
        log_tool_result("search_memory", result, success=True)
        return result
    
    memories = []
    for item in results:
        memories.append(f"- {item.get('key')}: {item.get('value')}")
    
    result = f"Found {len(results)} matching memories:\n" + "\n".join(memories)
    log_tool_result("search_memory", result, success=True)
    return result


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
    log_tool_call("delete_memory", {"key": context_key})
    
    memory = get_memory_manager()
    analytics = get_analytics_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        result = "Memory storage is currently unavailable (Redis not connected)."
        log_tool_result("delete_memory", result, success=False)
        return result
    
    success = memory.delete_context(uid, context_key)
    
    # Log to analytics
    analytics.log_memory_operation("delete", uid, context_key, success)
    
    if success:
        log_memory_operation("DELETE", context_key)
        result = f"Deleted memory: {context_key}"
        log_tool_result("delete_memory", result, success=True)
        return result
    else:
        result = f"Failed to delete memory '{context_key}'. It may not exist."
        log_tool_result("delete_memory", result, success=False)
        return result


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
    log_tool_call("get_conversation_history", {"limit": limit})
    
    memory = get_memory_manager()
    
    uid = user_id or DEFAULT_USER_ID
    
    if not memory.is_available():
        result = "Memory storage is currently unavailable (Redis not connected)."
        log_tool_result("get_conversation_history", result, success=False)
        return result
    
    conversations = memory.get_recent_conversations(uid, limit)
    
    if not conversations:
        result = "No conversation history found."
        log_tool_result("get_conversation_history", result, success=True)
        return result
    
    summaries = []
    for i, conv in enumerate(conversations, 1):
        topic = conv.get("topic", "Unknown topic")
        timestamp = conv.get("timestamp", "Unknown time")
        questions = conv.get("questions_asked", 0)
        summaries.append(f"{i}. {topic} ({timestamp}) - {questions} questions asked")
    
    result = f"Recent {len(conversations)} conversations:\n" + "\n".join(summaries)
    log_tool_result("get_conversation_history", result, success=True)
    return result

"""
Zero Me - Conversation Context Tools
Tools for accessing the full conversation transcript from the parallel Deepgram STT service.
"""

from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from loguru import logger
from datetime import datetime


# ============================================
# GLOBAL CONVERSATION STORE
# ============================================

class ConversationStore:
    """
    Thread-safe store for conversation transcripts captured by Deepgram STT.
    
    This store is populated by the parallel STT pipeline branch and can be
    accessed by agents via the get_conversation_context tool.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.transcripts: List[Dict[str, Any]] = []
        self.conversation_start: Optional[datetime] = None
        self.current_session_id: Optional[str] = None
        self._initialized = True
    
    def start_session(self, session_id: str = None):
        """Start a new conversation session."""
        import uuid
        self.current_session_id = session_id or str(uuid.uuid4())[:8]
        self.conversation_start = datetime.utcnow()
        self.transcripts = []
        logger.info(f"📝 ConversationStore: New session started - {self.current_session_id}")
    
    def add_user_transcript(self, text: str, timestamp: datetime = None, is_final: bool = True):
        """Add a user transcript from Deepgram STT."""
        if not text or not text.strip():
            return
        
        entry = {
            "role": "user",
            "content": text.strip(),
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
            "is_final": is_final,
            "session_id": self.current_session_id,
        }
        
        # If it's an interim result, update the last user entry if it exists
        if not is_final and self.transcripts and self.transcripts[-1]["role"] == "user":
            self.transcripts[-1] = entry
        else:
            self.transcripts.append(entry)
        
        if is_final:
            logger.debug(f"📝 User transcript: {text[:50]}...")
    
    def add_assistant_transcript(self, text: str, timestamp: datetime = None):
        """Add an assistant transcript (from Gemini Live responses)."""
        if not text or not text.strip():
            return
        
        entry = {
            "role": "assistant",
            "content": text.strip(),
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
            "is_final": True,
            "session_id": self.current_session_id,
        }
        self.transcripts.append(entry)
        logger.debug(f"📝 Assistant transcript: {text[:50]}...")
    
    def get_full_transcript(self) -> str:
        """Get the full conversation transcript as formatted text."""
        if not self.transcripts:
            return "No conversation recorded yet."
        
        lines = []
        for entry in self.transcripts:
            if entry.get("is_final", True):  # Only include final transcripts
                role = "User" if entry["role"] == "user" else "Assistant"
                lines.append(f"{role}: {entry['content']}")
        
        return "\n".join(lines)
    
    def get_transcript_messages(self) -> List[Dict[str, str]]:
        """Get transcripts as a list of message dicts for LLM context."""
        return [
            {"role": entry["role"], "content": entry["content"]}
            for entry in self.transcripts
            if entry.get("is_final", True)
        ]
    
    def get_last_n_messages(self, n: int = 10) -> str:
        """Get the last N messages as formatted text."""
        if not self.transcripts:
            return "No conversation recorded yet."
        
        # Filter to final transcripts only
        final_transcripts = [t for t in self.transcripts if t.get("is_final", True)]
        recent = final_transcripts[-n:] if len(final_transcripts) > n else final_transcripts
        
        lines = []
        for entry in recent:
            role = "User" if entry["role"] == "user" else "Assistant"
            lines.append(f"{role}: {entry['content']}")
        
        return "\n".join(lines)
    
    def get_user_messages_only(self) -> str:
        """Get only user messages from the transcript."""
        user_messages = [
            entry["content"] 
            for entry in self.transcripts 
            if entry["role"] == "user" and entry.get("is_final", True)
        ]
        return "\n".join(user_messages) if user_messages else "No user messages recorded."
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session metadata."""
        final_count = len([t for t in self.transcripts if t.get("is_final", True)])
        user_count = len([t for t in self.transcripts if t["role"] == "user" and t.get("is_final", True)])
        assistant_count = final_count - user_count
        
        return {
            "session_id": self.current_session_id,
            "started_at": self.conversation_start.isoformat() if self.conversation_start else None,
            "total_messages": final_count,
            "user_messages": user_count,
            "assistant_messages": assistant_count,
        }
    
    def clear(self):
        """Clear the conversation store."""
        self.transcripts = []
        self.conversation_start = None
        self.current_session_id = None


# Global singleton instance
_conversation_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    """Get the global conversation store instance."""
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = ConversationStore()
    return _conversation_store


# ============================================
# LANGCHAIN TOOLS
# ============================================

@tool
def get_conversation_context(
    mode: str = "full",
    last_n: int = 10,
) -> str:
    """
    Get the full conversation transcript from the current session.
    
    This tool provides access to the complete conversation history captured
    by the parallel Deepgram STT service. Use this to understand what has
    been discussed in the conversation.
    
    Args:
        mode: How to retrieve the context:
            - "full": Get the entire conversation transcript
            - "recent": Get only the last N messages (default 10)
            - "user_only": Get only user messages
            - "summary": Get session info with message counts
        last_n: Number of messages to retrieve when mode="recent" (default 10)
    
    Returns:
        The conversation context based on the selected mode
    
    Examples:
        - get_conversation_context(mode="full") → Full transcript
        - get_conversation_context(mode="recent", last_n=5) → Last 5 messages
        - get_conversation_context(mode="user_only") → Only user messages
        - get_conversation_context(mode="summary") → Session statistics
    """
    store = get_conversation_store()
    
    try:
        if mode == "full":
            result = store.get_full_transcript()
            logger.info(f"📖 Retrieved full conversation context ({len(result)} chars)")
            return result
        
        elif mode == "recent":
            result = store.get_last_n_messages(last_n)
            logger.info(f"📖 Retrieved last {last_n} messages")
            return result
        
        elif mode == "user_only":
            result = store.get_user_messages_only()
            logger.info(f"📖 Retrieved user-only messages")
            return result
        
        elif mode == "summary":
            info = store.get_session_info()
            result = f"""Session: {info['session_id']}
Started: {info['started_at']}
Total messages: {info['total_messages']}
User messages: {info['user_messages']}
Assistant messages: {info['assistant_messages']}"""
            logger.info(f"📖 Retrieved session summary")
            return result
        
        else:
            return f"Unknown mode: {mode}. Use 'full', 'recent', 'user_only', or 'summary'."
    
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        return f"Error retrieving conversation context: {str(e)}"


@tool
def search_conversation(query: str) -> str:
    """
    Search the conversation transcript for specific content.
    
    Use this to find specific topics, mentions, or information that was
    discussed earlier in the conversation.
    
    Args:
        query: The search term to look for in the conversation
    
    Returns:
        Matching messages from the conversation
    """
    store = get_conversation_store()
    
    try:
        query_lower = query.lower()
        matches = []
        
        for entry in store.transcripts:
            if not entry.get("is_final", True):
                continue
            
            if query_lower in entry["content"].lower():
                role = "User" if entry["role"] == "user" else "Assistant"
                matches.append(f"{role}: {entry['content']}")
        
        if matches:
            result = f"Found {len(matches)} matches for '{query}':\n\n" + "\n\n".join(matches)
            logger.info(f"🔍 Found {len(matches)} matches for '{query}'")
            return result
        else:
            logger.info(f"🔍 No matches found for '{query}'")
            return f"No matches found for '{query}' in the conversation."
    
    except Exception as e:
        logger.error(f"Error searching conversation: {e}")
        return f"Error searching conversation: {str(e)}"

"""
Zero Me - Real-time Tool Status Broadcasting
Tracks and broadcasts tool calls, agent status, and architecture flow in real-time.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger
import time


class NodeType(str, Enum):
    VOICE_AGENT = "voice_agent"
    MAIN_AGENT = "main_agent"
    DOC_AGENT = "doc_agent"
    TODO_AGENT = "todo_agent"
    EMAIL_AGENT = "email_agent"
    CALENDAR_AGENT = "calendar_agent"
    PERSONALITY_ENHANCER = "personality_enhancer"
    MEMORY = "memory"
    NOTION = "notion"
    EMAIL_SERVICE = "email_service"
    WANDB = "wandb"


class ToolCallStatus(str, Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ToolCall:
    """Represents a single tool call event."""
    id: str
    tool_name: str
    node_from: NodeType
    node_to: NodeType
    status: ToolCallStatus
    params: Dict[str, Any]
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: float = 0
    completed_at: Optional[float] = None
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "node_from": self.node_from.value,
            "node_to": self.node_to.value,
            "status": self.status.value,
            "params": self.params,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


@dataclass
class SessionStats:
    """Real-time session statistics."""
    session_id: str
    started_at: float
    tool_calls_total: int = 0
    tool_calls_success: int = 0
    tool_calls_error: int = 0
    tasks_delegated: int = 0
    memories_accessed: int = 0
    questions_asked: int = 0
    active_node: Optional[NodeType] = None
    active_tool: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "duration_seconds": time.time() - self.started_at,
            "tool_calls_total": self.tool_calls_total,
            "tool_calls_success": self.tool_calls_success,
            "tool_calls_error": self.tool_calls_error,
            "tasks_delegated": self.tasks_delegated,
            "memories_accessed": self.memories_accessed,
            "questions_asked": self.questions_asked,
            "active_node": self.active_node.value if self.active_node else None,
            "active_tool": self.active_tool,
        }


class ToolStatusBroadcaster:
    """
    Singleton broadcaster for real-time tool status updates.
    Frontend connects via SSE to receive updates.
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
        
        self._initialized = True
        self._subscribers: List[asyncio.Queue] = []
        self._call_counter = 0
        self._current_session: Optional[SessionStats] = None
        self._recent_calls: List[ToolCall] = []
        self._max_recent_calls = 50
        
        # Architecture nodes configuration
        self._architecture = {
            "nodes": [
                {"id": "voice_agent", "label": "Casey (Voice)", "type": "agent", "x": 400, "y": 50},
                {"id": "main_agent", "label": "Task Dispatcher", "type": "agent", "x": 400, "y": 150},
                {"id": "doc_agent", "label": "Doc Agent", "type": "agent", "x": 200, "y": 250},
                {"id": "todo_agent", "label": "Todo Agent", "type": "agent", "x": 350, "y": 250},
                {"id": "email_agent", "label": "Email Agent", "type": "agent", "x": 500, "y": 250},
                {"id": "calendar_agent", "label": "Calendar Agent", "type": "agent", "x": 650, "y": 250},
                {"id": "memory", "label": "Memory (Redis)", "type": "service", "x": 100, "y": 150},
                {"id": "notion", "label": "Notion", "type": "integration", "x": 350, "y": 350},
                {"id": "email_service", "label": "Resend", "type": "integration", "x": 500, "y": 350},
                {"id": "wandb", "label": "WandB", "type": "integration", "x": 650, "y": 350},
                {"id": "personality_enhancer", "label": "Personality Enhancer", "type": "agent", "x": 100, "y": 350},
            ],
            "edges": [
                {"from": "voice_agent", "to": "main_agent", "label": "delegate_task"},
                {"from": "voice_agent", "to": "memory", "label": "remember/recall"},
                {"from": "main_agent", "to": "doc_agent", "label": "doc tasks"},
                {"from": "main_agent", "to": "todo_agent", "label": "todo tasks"},
                {"from": "main_agent", "to": "email_agent", "label": "email tasks"},
                {"from": "main_agent", "to": "calendar_agent", "label": "calendar tasks"},
                {"from": "doc_agent", "to": "notion", "label": "create/read"},
                {"from": "todo_agent", "to": "notion", "label": "add/get"},
                {"from": "calendar_agent", "to": "notion", "label": "events"},
                {"from": "email_agent", "to": "email_service", "label": "send"},
                {"from": "doc_agent", "to": "memory", "label": "context"},
                {"from": "todo_agent", "to": "memory", "label": "context"},
                {"from": "calendar_agent", "to": "memory", "label": "context"},
                {"from": "email_agent", "to": "memory", "label": "context"},
                {"from": "personality_enhancer", "to": "memory", "label": "analyze"},
                {"from": "personality_enhancer", "to": "wandb", "label": "log"},
            ]
        }
        
        logger.info("ToolStatusBroadcaster initialized")
    
    def start_session(self, session_id: str):
        """Start a new session for tracking."""
        self._current_session = SessionStats(
            session_id=session_id,
            started_at=time.time()
        )
        self._recent_calls = []
        self._broadcast_event("session_start", self._current_session.to_dict())
        logger.info(f"📊 Session started: {session_id}")
    
    def end_session(self):
        """End the current session."""
        if self._current_session:
            self._broadcast_event("session_end", self._current_session.to_dict())
            logger.info(f"📊 Session ended: {self._current_session.session_id}")
            self._current_session = None
    
    def start_tool_call(
        self,
        tool_name: str,
        node_from: NodeType,
        node_to: NodeType,
        params: Dict[str, Any]
    ) -> str:
        """
        Record the start of a tool call.
        Returns call_id for tracking.
        """
        self._call_counter += 1
        call_id = f"call_{self._call_counter}_{int(time.time() * 1000)}"
        
        call = ToolCall(
            id=call_id,
            tool_name=tool_name,
            node_from=node_from,
            node_to=node_to,
            status=ToolCallStatus.STARTED,
            params=params,
            started_at=time.time()
        )
        
        self._recent_calls.append(call)
        if len(self._recent_calls) > self._max_recent_calls:
            self._recent_calls.pop(0)
        
        # Update session stats
        if self._current_session:
            self._current_session.tool_calls_total += 1
            self._current_session.active_node = node_to
            self._current_session.active_tool = tool_name
            
            if "memory" in tool_name.lower() or node_to == NodeType.MEMORY:
                self._current_session.memories_accessed += 1
            if tool_name == "delegate_task":
                self._current_session.tasks_delegated += 1
        
        self._broadcast_event("tool_call_start", call.to_dict())
        logger.debug(f"📤 Tool call started: {tool_name} ({node_from.value} → {node_to.value})")
        
        return call_id
    
    def complete_tool_call(
        self,
        call_id: str,
        result: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record the completion of a tool call."""
        call = next((c for c in self._recent_calls if c.id == call_id), None)
        
        if call:
            call.status = ToolCallStatus.SUCCESS if success else ToolCallStatus.ERROR
            call.result = result[:200] if result else None  # Truncate for broadcast
            call.error = error
            call.completed_at = time.time()
            call.duration_ms = (call.completed_at - call.started_at) * 1000
            
            # Update session stats
            if self._current_session:
                if success:
                    self._current_session.tool_calls_success += 1
                else:
                    self._current_session.tool_calls_error += 1
                self._current_session.active_node = None
                self._current_session.active_tool = None
            
            self._broadcast_event("tool_call_complete", call.to_dict())
            logger.debug(f"📥 Tool call completed: {call.tool_name} ({call.duration_ms:.0f}ms)")
    
    def set_active_node(self, node: NodeType):
        """Set the currently active node (for visualization)."""
        if self._current_session:
            self._current_session.active_node = node
            self._broadcast_event("active_node", {"node": node.value})
    
    def record_question_asked(self):
        """Record when the bot asks the user a question."""
        if self._current_session:
            self._current_session.questions_asked += 1
            self._broadcast_event("question_asked", {
                "count": self._current_session.questions_asked
            })
    
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to receive tool status updates."""
        queue = asyncio.Queue()
        self._subscribers.append(queue)
        logger.info(f"📡 New subscriber (total: {len(self._subscribers)})")
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from updates."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            logger.info(f"📡 Subscriber removed (total: {len(self._subscribers)})")
    
    def _broadcast_event(self, event_type: str, data: Dict):
        """Broadcast an event to all subscribers."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data
        }
        
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full, dropping event")
    
    def get_architecture(self) -> Dict:
        """Get the architecture configuration for visualization."""
        return self._architecture
    
    def get_current_stats(self) -> Optional[Dict]:
        """Get current session statistics."""
        if self._current_session:
            return self._current_session.to_dict()
        return None
    
    def get_recent_calls(self, limit: int = 10) -> List[Dict]:
        """Get recent tool calls."""
        return [call.to_dict() for call in self._recent_calls[-limit:]]


# Global instance
_broadcaster: Optional[ToolStatusBroadcaster] = None


def get_tool_status_broadcaster() -> ToolStatusBroadcaster:
    """Get the global tool status broadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = ToolStatusBroadcaster()
    return _broadcaster


# Convenience functions for easy integration
def broadcast_tool_start(
    tool_name: str,
    node_from: str,
    node_to: str,
    params: Dict[str, Any] = None
) -> str:
    """Convenience function to broadcast tool call start."""
    broadcaster = get_tool_status_broadcaster()
    return broadcaster.start_tool_call(
        tool_name=tool_name,
        node_from=NodeType(node_from),
        node_to=NodeType(node_to),
        params=params or {}
    )


def broadcast_tool_complete(
    call_id: str,
    result: str,
    success: bool = True,
    error: str = None
):
    """Convenience function to broadcast tool call completion."""
    broadcaster = get_tool_status_broadcaster()
    broadcaster.complete_tool_call(call_id, result, success, error)

"""
Zero Me - Tool Logging Utilities
Colorful logging for tool calls and results with real-time broadcasting
"""

from loguru import logger
from typing import Dict, Any, Optional

# ANSI color codes for terminal output
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Track active tool calls for completion
_active_calls: Dict[str, str] = {}  # tool_name -> call_id


def _get_broadcaster():
    """Lazy import to avoid circular dependencies."""
    try:
        from tool_status import get_tool_status_broadcaster, NodeType
        return get_tool_status_broadcaster(), NodeType
    except ImportError:
        return None, None


def _get_node_for_tool(tool_name: str):
    """Determine which node a tool belongs to."""
    _, NodeType = _get_broadcaster()
    if NodeType is None:
        return None, None
    
    tool_mapping = {
        # Notion tools
        "add_todo": (NodeType.TODO_AGENT, NodeType.NOTION),
        "get_todos": (NodeType.TODO_AGENT, NodeType.NOTION),
        "update_todo": (NodeType.TODO_AGENT, NodeType.NOTION),
        "add_calendar_event": (NodeType.CALENDAR_AGENT, NodeType.NOTION),
        "get_calendar_events": (NodeType.CALENDAR_AGENT, NodeType.NOTION),
        "update_calendar_event": (NodeType.CALENDAR_AGENT, NodeType.NOTION),
        "delete_calendar_event": (NodeType.CALENDAR_AGENT, NodeType.NOTION),
        "create_notion_page": (NodeType.DOC_AGENT, NodeType.NOTION),
        "read_notion_page": (NodeType.DOC_AGENT, NodeType.NOTION),
        "search_notion": (NodeType.DOC_AGENT, NodeType.NOTION),
        # Memory tools
        "store_memory": (NodeType.VOICE_AGENT, NodeType.MEMORY),
        "retrieve_memory": (NodeType.VOICE_AGENT, NodeType.MEMORY),
        "search_memory": (NodeType.VOICE_AGENT, NodeType.MEMORY),
        "delete_memory": (NodeType.VOICE_AGENT, NodeType.MEMORY),
        "get_conversation_history": (NodeType.VOICE_AGENT, NodeType.MEMORY),
        # Email tools
        "send_email": (NodeType.EMAIL_AGENT, NodeType.EMAIL_SERVICE),
        "draft_email": (NodeType.EMAIL_AGENT, NodeType.EMAIL_SERVICE),
        "check_email_status": (NodeType.EMAIL_AGENT, NodeType.EMAIL_SERVICE),
        # Analytics tools
        "log_metric": (NodeType.PERSONALITY_ENHANCER, NodeType.WANDB),
        "log_question_count": (NodeType.PERSONALITY_ENHANCER, NodeType.WANDB),
        "log_parameter_change": (NodeType.PERSONALITY_ENHANCER, NodeType.WANDB),
        "record_conversation_analytics": (NodeType.PERSONALITY_ENHANCER, NodeType.WANDB),
        "get_current_parameters": (NodeType.PERSONALITY_ENHANCER, NodeType.WANDB),
    }
    
    return tool_mapping.get(tool_name, (NodeType.MAIN_AGENT, NodeType.MAIN_AGENT))


def log_tool_call(tool_name: str, params: dict) -> Optional[str]:
    """Log a tool call with yellow/gold color and broadcast."""
    params_str = ", ".join(f"{k}='{v}'" if isinstance(v, str) else f"{k}={v}" for k, v in params.items())
    # Truncate long values
    if len(params_str) > 100:
        params_str = params_str[:100] + "..."
    
    print(f"\n{YELLOW}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{YELLOW}{BOLD}║  🔧 TOOL CALL: {tool_name}{RESET}")
    print(f"{YELLOW}║  📥 Params: {params_str}{RESET}")
    print(f"{YELLOW}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}\n")
    
    logger.opt(colors=True).info(f"<yellow>🔧 TOOL: {tool_name}({params_str})</yellow>")
    
    # Broadcast to frontend
    broadcaster, _ = _get_broadcaster()
    if broadcaster:
        node_from, node_to = _get_node_for_tool(tool_name)
        if node_from and node_to:
            call_id = broadcaster.start_tool_call(
                tool_name=tool_name,
                node_from=node_from,
                node_to=node_to,
                params=params
            )
            _active_calls[tool_name] = call_id
            return call_id
    
    return None


def log_tool_result(tool_name: str, result: str, success: bool = True, call_id: str = None):
    """Log a tool result with magenta/purple color and broadcast."""
    # Truncate long results
    display_result = result[:150] + "..." if len(result) > 150 else result
    
    color = MAGENTA if success else RED
    icon = "✅" if success else "❌"
    
    print(f"{color}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{color}{BOLD}║  {icon} RESULT: {tool_name}{RESET}")
    print(f"{color}║  📤 {display_result}{RESET}")
    print(f"{color}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}\n")
    
    if success:
        logger.opt(colors=True).info(f"<magenta>✅ {tool_name} → {display_result}</magenta>")
    else:
        logger.opt(colors=True).error(f"<red>❌ {tool_name} → {display_result}</red>")
    
    # Broadcast completion to frontend
    broadcaster, _ = _get_broadcaster()
    if broadcaster:
        # Use provided call_id or look up from active calls
        actual_call_id = call_id or _active_calls.pop(tool_name, None)
        if actual_call_id:
            broadcaster.complete_tool_call(
                call_id=actual_call_id,
                result=result,
                success=success,
                error=None if success else result
            )


def log_tool_start(tool_name: str):
    """Log when a tool starts executing."""
    print(f"{CYAN}⚡ Executing {tool_name}...{RESET}")


def log_memory_operation(operation: str, key: str, value: str = None):
    """Log memory operations with purple color."""
    if value:
        display_value = value[:50] + "..." if len(value) > 50 else value
        print(f"{MAGENTA}💾 MEMORY {operation.upper()}: {key} = {display_value}{RESET}")
    else:
        print(f"{MAGENTA}💾 MEMORY {operation.upper()}: {key}{RESET}")
    
    logger.opt(colors=True).info(f"<magenta>💾 MEMORY {operation}: {key}</magenta>")


def log_agent_delegation(from_agent: str, to_agent: str, task: str):
    """Log agent delegation with cyan color."""
    task_preview = task[:80] + "..." if len(task) > 80 else task
    print(f"\n{CYAN}{BOLD}🔀 DELEGATION: {from_agent} → {to_agent}{RESET}")
    print(f"{CYAN}   Task: {task_preview}{RESET}\n")
    
    logger.opt(colors=True).info(f"<cyan>🔀 {from_agent} → {to_agent}: {task_preview}</cyan>")

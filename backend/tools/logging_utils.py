"""
Zero Me - Tool Logging Utilities
Colorful logging for tool calls and results
"""

from loguru import logger

# ANSI color codes for terminal output
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def log_tool_call(tool_name: str, params: dict):
    """Log a tool call with yellow/gold color."""
    params_str = ", ".join(f"{k}='{v}'" if isinstance(v, str) else f"{k}={v}" for k, v in params.items())
    # Truncate long values
    if len(params_str) > 100:
        params_str = params_str[:100] + "..."
    
    print(f"\n{YELLOW}{BOLD}╔══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{YELLOW}{BOLD}║  🔧 TOOL CALL: {tool_name}{RESET}")
    print(f"{YELLOW}║  📥 Params: {params_str}{RESET}")
    print(f"{YELLOW}{BOLD}╚══════════════════════════════════════════════════════════════╝{RESET}\n")
    
    logger.opt(colors=True).info(f"<yellow>🔧 TOOL: {tool_name}({params_str})</yellow>")


def log_tool_result(tool_name: str, result: str, success: bool = True):
    """Log a tool result with magenta/purple color."""
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

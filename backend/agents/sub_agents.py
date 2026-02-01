"""
Zero Me - Sub-Agents
Individual agents for Doc, Todo, Email, and Calendar operations
Using LangChain with Gemini models

All agents have access to memory retrieval for user context.
"""

import os
from typing import Optional, List, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from loguru import logger

# Import parameters
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parameters import (
    DOC_AGENT_CONFIG,
    DOC_AGENT_SYSTEM_PROMPT,
    TODO_AGENT_CONFIG,
    TODO_AGENT_SYSTEM_PROMPT,
    EMAIL_AGENT_CONFIG,
    EMAIL_AGENT_SYSTEM_PROMPT,
    CALENDAR_AGENT_CONFIG,
    CALENDAR_AGENT_SYSTEM_PROMPT,
)

# Import tools
from tools.notion_tools import (
    create_notion_page,
    read_notion_page,
    search_notion,
    add_todo,
    get_todos,
    update_todo,
    add_calendar_event,
    get_calendar_events,
    update_calendar_event,
    delete_calendar_event,
)
from tools.email_tools import send_email, draft_email, check_email_status
from tools.memory_tools import retrieve_memory, search_memory


# Memory context addition to all agent prompts
MEMORY_CONTEXT_PROMPT = """

## User Memory Access
You have access to the user's stored memories via these tools:
- retrieve_memory: Get specific remembered info (e.g., preferred_name, email, preferences)
- search_memory: Search for relevant memories by keyword

ALWAYS check memory for relevant context before completing tasks. For example:
- Before sending an email, check if you know the user's name to sign properly
- Before creating a todo, check if there's related context
- Use the user's preferred name if stored

Example: If the task is "send email to boss", first search_memory("boss") to get their email address.
"""


def create_llm(config: dict) -> ChatGoogleGenerativeAI:
    """Create a ChatGoogleGenerativeAI instance from config."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment")
    
    return ChatGoogleGenerativeAI(
        model=config.get("model", "gemini-3-flash-preview"),
        temperature=config.get("temperature", 0.5),
        google_api_key=api_key,
    )


def create_agent_graph(
    llm: ChatGoogleGenerativeAI,
    tools: List[Any],
    system_prompt: str,
    agent_name: str,
):
    """Create a langgraph react agent with the given LLM, tools, and prompt."""
    from langchain_core.messages import SystemMessage
    
    # Add memory context to the system prompt
    enhanced_prompt = system_prompt + MEMORY_CONTEXT_PROMPT
    
    # Create react agent using langgraph with system message
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SystemMessage(content=enhanced_prompt),
    )
    
    logger.info(f"Created {agent_name} with {len(tools)} tools (including memory access)")
    return agent


# ============================================
# DOC AGENT
# ============================================

class DocAgent:
    """Agent for document operations using Notion."""
    
    def __init__(self):
        self.name = DOC_AGENT_CONFIG["name"]
        self.llm = create_llm(DOC_AGENT_CONFIG)
        self.tools = [
            create_notion_page,
            read_notion_page,
            search_notion,
            # Memory tools for context
            retrieve_memory,
            search_memory,
        ]
        self.agent = create_agent_graph(
            self.llm,
            self.tools,
            DOC_AGENT_SYSTEM_PROMPT,
            self.name,
        )
    
    async def run(self, task: str, chat_history: Optional[List] = None) -> str:
        """Execute a document task."""
        try:
            messages = [{"role": "user", "content": task}]
            result = await self.agent.ainvoke({"messages": messages})
            # Get the last AI message content
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "content") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "Task completed but no output returned."
        except Exception as e:
            logger.error(f"DocAgent error: {e}")
            return f"Error processing document task: {str(e)}"


def create_doc_agent() -> DocAgent:
    """Factory function to create a DocAgent."""
    return DocAgent()


# ============================================
# TODO AGENT
# ============================================

class TodoAgent:
    """Agent for todo/task operations using Notion."""
    
    def __init__(self):
        self.name = TODO_AGENT_CONFIG["name"]
        self.llm = create_llm(TODO_AGENT_CONFIG)
        self.tools = [
            add_todo,
            get_todos,
            update_todo,
            search_notion,  # For finding todos by name
            # Memory tools for context
            retrieve_memory,
            search_memory,
        ]
        self.agent = create_agent_graph(
            self.llm,
            self.tools,
            TODO_AGENT_SYSTEM_PROMPT,
            self.name,
        )
    
    async def run(self, task: str, chat_history: Optional[List] = None) -> str:
        """Execute a todo task."""
        try:
            messages = [{"role": "user", "content": task}]
            result = await self.agent.ainvoke({"messages": messages})
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "content") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "Task completed but no output returned."
        except Exception as e:
            logger.error(f"TodoAgent error: {e}")
            return f"Error processing todo task: {str(e)}"


def create_todo_agent() -> TodoAgent:
    """Factory function to create a TodoAgent."""
    return TodoAgent()


# ============================================
# EMAIL AGENT
# ============================================

class EmailAgent:
    """Agent for email operations using Resend."""
    
    def __init__(self):
        self.name = EMAIL_AGENT_CONFIG["name"]
        self.llm = create_llm(EMAIL_AGENT_CONFIG)
        self.tools = [
            send_email,
            draft_email,
            check_email_status,
            # Memory tools for context
            retrieve_memory,
            search_memory,
        ]
        self.agent = create_agent_graph(
            self.llm,
            self.tools,
            EMAIL_AGENT_SYSTEM_PROMPT,
            self.name,
        )
    
    async def run(self, task: str, chat_history: Optional[List] = None) -> str:
        """Execute an email task."""
        try:
            messages = [{"role": "user", "content": task}]
            result = await self.agent.ainvoke({"messages": messages})
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "content") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "Task completed but no output returned."
        except Exception as e:
            logger.error(f"EmailAgent error: {e}")
            return f"Error processing email task: {str(e)}"


def create_email_agent() -> EmailAgent:
    """Factory function to create an EmailAgent."""
    return EmailAgent()


# ============================================
# CALENDAR AGENT
# ============================================

class CalendarAgent:
    """Agent for calendar operations using Notion."""
    
    def __init__(self):
        self.name = CALENDAR_AGENT_CONFIG["name"]
        self.llm = create_llm(CALENDAR_AGENT_CONFIG)
        self.tools = [
            add_calendar_event,
            get_calendar_events,
            update_calendar_event,
            delete_calendar_event,
            search_notion,  # For finding events
            # Memory tools for context
            retrieve_memory,
            search_memory,
        ]
        self.agent = create_agent_graph(
            self.llm,
            self.tools,
            CALENDAR_AGENT_SYSTEM_PROMPT,
            self.name,
        )
    
    async def run(self, task: str, chat_history: Optional[List] = None) -> str:
        """Execute a calendar task."""
        try:
            messages = [{"role": "user", "content": task}]
            result = await self.agent.ainvoke({"messages": messages})
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "content") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "Task completed but no output returned."
        except Exception as e:
            logger.error(f"CalendarAgent error: {e}")
            return f"Error processing calendar task: {str(e)}"


def create_calendar_agent() -> CalendarAgent:
    """Factory function to create a CalendarAgent."""
    return CalendarAgent()

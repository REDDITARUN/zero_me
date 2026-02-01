"""
Zero Me - Main Dispatcher Agent
Routes tasks to appropriate sub-agents
Using LangChain with Gemini models
"""

import os
import time
from typing import Optional, List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from loguru import logger

# Import parameters
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parameters import MAIN_AGENT_CONFIG, MAIN_AGENT_SYSTEM_PROMPT
from analytics import get_analytics_manager, weave_op, trace_agent_delegation

# Import sub-agents
from agents.sub_agents import (
    DocAgent,
    TodoAgent,
    EmailAgent,
    CalendarAgent,
    create_doc_agent,
    create_todo_agent,
    create_email_agent,
    create_calendar_agent,
)


class MainDispatcherAgent:
    """
    Main agent that dispatches tasks to sub-agents.
    
    This agent receives task requests from the voice agent and routes them
    to the appropriate sub-agent (doc, todo, email, calendar).
    """
    
    def __init__(self):
        self.name = MAIN_AGENT_CONFIG["name"]
        self.analytics = get_analytics_manager()
        
        # Initialize sub-agents lazily (created on first use)
        self._doc_agent: Optional[DocAgent] = None
        self._todo_agent: Optional[TodoAgent] = None
        self._email_agent: Optional[EmailAgent] = None
        self._calendar_agent: Optional[CalendarAgent] = None
        
        # Create the dispatcher LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        self.llm = ChatGoogleGenerativeAI(
            model=MAIN_AGENT_CONFIG.get("model", "gemini-3-flash-preview"),
            temperature=MAIN_AGENT_CONFIG.get("temperature", 0.3),
            google_api_key=api_key,
        )
        
        # Create dispatch tools
        self.tools = self._create_dispatch_tools()
        
        # Create the agent
        self.agent = self._create_agent()
        
        logger.info(f"MainDispatcherAgent initialized with {len(self.tools)} dispatch tools")
    
    @property
    def doc_agent(self) -> DocAgent:
        if self._doc_agent is None:
            self._doc_agent = create_doc_agent()
        return self._doc_agent
    
    @property
    def todo_agent(self) -> TodoAgent:
        if self._todo_agent is None:
            self._todo_agent = create_todo_agent()
        return self._todo_agent
    
    @property
    def email_agent(self) -> EmailAgent:
        if self._email_agent is None:
            self._email_agent = create_email_agent()
        return self._email_agent
    
    @property
    def calendar_agent(self) -> CalendarAgent:
        if self._calendar_agent is None:
            self._calendar_agent = create_calendar_agent()
        return self._calendar_agent
    
    def _create_dispatch_tools(self) -> List:
        """Create tools that dispatch to sub-agents."""
        
        # Store reference to self for closure
        dispatcher = self
        
        @tool
        async def delegate_to_doc_agent(task: str) -> str:
            """
            Delegate a document-related task to the Doc Agent.
            
            Use for: creating documents, reading documents, searching for documents.
            
            Args:
                task: Description of the document task to perform
            
            Returns:
                Result from the Doc Agent
            """
            start_time = time.time()
            try:
                result = await dispatcher.doc_agent.run(task)
                success = "error" not in result.lower()
                dispatcher.analytics.log_agent_call(
                    "doc_agent",
                    "document_operation",
                    success,
                    (time.time() - start_time) * 1000,
                )
                return result
            except Exception as e:
                dispatcher.analytics.log_agent_call(
                    "doc_agent",
                    "document_operation",
                    False,
                    (time.time() - start_time) * 1000,
                )
                return f"Error from Doc Agent: {str(e)}"
        
        @tool
        async def delegate_to_todo_agent(task: str) -> str:
            """
            Delegate a todo/task-related request to the Todo Agent.
            
            Use for: adding todos, getting todos, updating todos, completing tasks.
            
            Args:
                task: Description of the todo task to perform
            
            Returns:
                Result from the Todo Agent
            """
            start_time = time.time()
            try:
                result = await dispatcher.todo_agent.run(task)
                success = "error" not in result.lower()
                dispatcher.analytics.log_agent_call(
                    "todo_agent",
                    "todo_operation",
                    success,
                    (time.time() - start_time) * 1000,
                )
                return result
            except Exception as e:
                dispatcher.analytics.log_agent_call(
                    "todo_agent",
                    "todo_operation",
                    False,
                    (time.time() - start_time) * 1000,
                )
                return f"Error from Todo Agent: {str(e)}"
        
        @tool
        async def delegate_to_email_agent(task: str) -> str:
            """
            Delegate an email-related task to the Email Agent.
            
            Use for: sending emails, drafting emails, checking email status.
            
            Args:
                task: Description of the email task to perform
            
            Returns:
                Result from the Email Agent
            """
            start_time = time.time()
            try:
                result = await dispatcher.email_agent.run(task)
                success = "error" not in result.lower()
                dispatcher.analytics.log_agent_call(
                    "email_agent",
                    "email_operation",
                    success,
                    (time.time() - start_time) * 1000,
                )
                return result
            except Exception as e:
                dispatcher.analytics.log_agent_call(
                    "email_agent",
                    "email_operation",
                    False,
                    (time.time() - start_time) * 1000,
                )
                return f"Error from Email Agent: {str(e)}"
        
        @tool
        async def delegate_to_calendar_agent(task: str) -> str:
            """
            Delegate a calendar-related task to the Calendar Agent.
            
            Use for: adding events, getting events, updating events, removing events.
            
            Args:
                task: Description of the calendar task to perform
            
            Returns:
                Result from the Calendar Agent
            """
            start_time = time.time()
            try:
                result = await dispatcher.calendar_agent.run(task)
                success = "error" not in result.lower()
                dispatcher.analytics.log_agent_call(
                    "calendar_agent",
                    "calendar_operation",
                    success,
                    (time.time() - start_time) * 1000,
                )
                return result
            except Exception as e:
                dispatcher.analytics.log_agent_call(
                    "calendar_agent",
                    "calendar_operation",
                    False,
                    (time.time() - start_time) * 1000,
                )
                return f"Error from Calendar Agent: {str(e)}"
        
        return [
            delegate_to_doc_agent,
            delegate_to_todo_agent,
            delegate_to_email_agent,
            delegate_to_calendar_agent,
        ]
    
    def _create_agent(self):
        """Create the langgraph react agent."""
        from langchain_core.messages import SystemMessage
        
        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=SystemMessage(content=MAIN_AGENT_SYSTEM_PROMPT),
        )
    
    async def dispatch(self, task: str, chat_history: Optional[List] = None) -> str:
        """
        Dispatch a task to the appropriate sub-agent.
        
        Args:
            task: The task to dispatch
            chat_history: Optional conversation history
        
        Returns:
            Result from the sub-agent
        """
        start_time = time.time()
        try:
            logger.info(f"Dispatching task: {task[:100]}...")
            
            messages = [{"role": "user", "content": task}]
            result = await self.agent.ainvoke({"messages": messages})
            
            # Get the last AI message content
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
            if ai_messages:
                output = ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            else:
                output = "Task completed but no output returned."
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"Task completed in {duration_ms:.0f}ms: {output[:100]}...")
            
            # Trace to Weave
            trace_agent_delegation(
                from_agent="voice_agent",
                to_agent="main_dispatcher",
                task=task,
                result=output,
                duration_ms=duration_ms,
            )
            
            return output
            
        except Exception as e:
            logger.error(f"MainDispatcherAgent error: {e}")
            return f"Error dispatching task: {str(e)}"


# Global instance
_main_agent: Optional[MainDispatcherAgent] = None


def create_main_agent() -> MainDispatcherAgent:
    """Get or create the main dispatcher agent."""
    global _main_agent
    if _main_agent is None:
        _main_agent = MainDispatcherAgent()
    return _main_agent


def get_main_agent() -> MainDispatcherAgent:
    """Get the main agent instance (creates if needed)."""
    return create_main_agent()

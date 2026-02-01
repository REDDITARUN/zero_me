"""
Zero Me - Personality Enhancer Agent
Manages memory, analytics, and parameter optimization
Using LangChain with Gemini models
"""

import os
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from loguru import logger

# Import parameters
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parameters import PERSONALITY_ENHANCER_CONFIG, PERSONALITY_ENHANCER_SYSTEM_PROMPT
from memory import get_memory_manager
from analytics import get_analytics_manager

# Import tools
from tools.memory_tools import (
    store_memory,
    retrieve_memory,
    search_memory,
    delete_memory,
    get_conversation_history,
)
from tools.analytics_tools import (
    log_metric,
    log_question_count,
    log_parameter_change,
    modify_agent_parameter,
    get_current_parameters,
    record_conversation_analytics,
)


class PersonalityEnhancerAgent:
    """
    Agent that enhances the system's personalization over time.
    
    Responsibilities:
    1. Store and retrieve personal context from memory
    2. Track conversation analytics (questions asked, topics, etc.)
    3. Suggest/apply parameter changes for optimization
    """
    
    def __init__(self):
        self.name = PERSONALITY_ENHANCER_CONFIG["name"]
        self.memory = get_memory_manager()
        self.analytics = get_analytics_manager()
        
        # Track conversation metrics
        self.current_conversation = {
            "start_time": None,
            "questions_asked": 0,
            "tasks_delegated": 0,
            "topics": [],
        }
        
        # Create the LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        self.llm = ChatGoogleGenerativeAI(
            model=PERSONALITY_ENHANCER_CONFIG.get("model", "gemini-3-flash-preview"),
            temperature=PERSONALITY_ENHANCER_CONFIG.get("temperature", 0.6),
            google_api_key=api_key,
        )
        
        # Create tools list
        self.tools = [
            store_memory,
            retrieve_memory,
            search_memory,
            delete_memory,
            get_conversation_history,
            log_metric,
            log_question_count,
            log_parameter_change,
            modify_agent_parameter,
            get_current_parameters,
            record_conversation_analytics,
        ]
        
        # Create the agent
        self.agent = self._create_agent()
        
        logger.info(f"PersonalityEnhancerAgent initialized with {len(self.tools)} tools")
    
    def _create_agent(self):
        """Create the langgraph react agent."""
        from langchain_core.messages import SystemMessage
        
        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=SystemMessage(content=PERSONALITY_ENHANCER_SYSTEM_PROMPT),
        )
    
    def start_conversation(self):
        """Mark the start of a new conversation."""
        self.current_conversation = {
            "start_time": datetime.utcnow(),
            "questions_asked": 0,
            "tasks_delegated": 0,
            "topics": [],
        }
        logger.info("New conversation started")
    
    def record_question(self):
        """Record that the voice agent asked a question."""
        self.current_conversation["questions_asked"] += 1
    
    def record_task_delegation(self):
        """Record that a task was delegated to a sub-agent."""
        self.current_conversation["tasks_delegated"] += 1
    
    def record_topic(self, topic: str):
        """Record a conversation topic."""
        if topic and topic not in self.current_conversation["topics"]:
            self.current_conversation["topics"].append(topic)
    
    async def end_conversation(self, user_id: str = "default_user") -> str:
        """
        End the current conversation and process analytics.
        
        This method:
        1. Calculates conversation duration
        2. Logs analytics to WandB
        3. Stores a conversation summary in memory
        4. Analyzes if any parameter adjustments are needed
        
        Args:
            user_id: User identifier
        
        Returns:
            Summary of conversation analytics
        """
        if not self.current_conversation["start_time"]:
            return "No active conversation to end."
        
        # Calculate duration
        end_time = datetime.utcnow()
        duration = (end_time - self.current_conversation["start_time"]).total_seconds()
        
        # Log to WandB
        self.analytics.log_conversation_end(
            user_id=user_id,
            questions_asked=self.current_conversation["questions_asked"],
            tasks_delegated=self.current_conversation["tasks_delegated"],
            duration_seconds=duration,
            topics=self.current_conversation["topics"],
        )
        
        # Store conversation summary in memory
        summary = {
            "topic": ", ".join(self.current_conversation["topics"]) or "General conversation",
            "questions_asked": self.current_conversation["questions_asked"],
            "tasks_delegated": self.current_conversation["tasks_delegated"],
            "duration_seconds": duration,
            "timestamp": end_time.isoformat(),
        }
        self.memory.store_conversation_summary(user_id, summary)
        
        # Generate summary string
        result = f"""
Conversation ended:
- Duration: {duration:.1f} seconds
- Questions asked: {self.current_conversation['questions_asked']}
- Tasks delegated: {self.current_conversation['tasks_delegated']}
- Topics: {', '.join(self.current_conversation['topics']) or 'None recorded'}
"""
        
        # Reset conversation tracking
        self.current_conversation = {
            "start_time": None,
            "questions_asked": 0,
            "tasks_delegated": 0,
            "topics": [],
        }
        
        return result
    
    async def analyze_and_store_context(
        self,
        conversation_text: str,
        user_id: str = "default_user",
    ) -> str:
        """
        Analyze a conversation and extract personal context to store.
        
        This is called after each conversation to learn about the user.
        
        Args:
            conversation_text: The full conversation text
            user_id: User identifier
        
        Returns:
            Summary of what was learned and stored
        """
        try:
            prompt = f"""
Analyze this conversation and extract any personal context worth remembering:

{conversation_text}

For each piece of context you find:
1. Use the store_memory tool to save it
2. Use descriptive keys like "preferred_name", "work_schedule", "project_focus", etc.

Only store genuinely useful context that would help personalize future conversations.
Don't store sensitive information like passwords or financial details.

After storing, provide a brief summary of what you learned.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.agent.ainvoke({"messages": messages})
            
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "Analysis completed."
            
        except Exception as e:
            logger.error(f"Error analyzing conversation: {e}")
            return f"Error analyzing conversation: {str(e)}"
    
    async def suggest_parameter_changes(self, feedback: str) -> str:
        """
        Analyze feedback and suggest parameter changes.
        
        Args:
            feedback: User feedback or observed patterns
        
        Returns:
            Suggested changes (not applied unless confirmed)
        """
        try:
            prompt = f"""
Based on this feedback/observation, analyze if any agent parameters should be adjusted:

{feedback}

Consider:
- Should any agent's temperature be adjusted?
- Are there patterns suggesting prompts need refinement?
- Is any agent underperforming?

Use get_current_parameters to see current values, then suggest changes.
DO NOT apply changes - just suggest them with reasoning.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.agent.ainvoke({"messages": messages})
            
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "Analysis completed."
            
        except Exception as e:
            logger.error(f"Error suggesting parameters: {e}")
            return f"Error analyzing parameters: {str(e)}"
    
    async def apply_parameter_change(
        self,
        agent_name: str,
        parameter_key: str,
        new_value: str,
        reason: str,
    ) -> str:
        """
        Apply a parameter change (use after suggestion is approved).
        
        Args:
            agent_name: Agent to modify
            parameter_key: Parameter to change
            new_value: New value
            reason: Why the change is being made
        
        Returns:
            Result of the change
        """
        try:
            prompt = f"""
Apply this parameter change:
- Agent: {agent_name}
- Parameter: {parameter_key}
- New Value: {new_value}
- Reason: {reason}

Use the modify_agent_parameter tool to make this change.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.agent.ainvoke({"messages": messages})
            
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "Change applied."
            
        except Exception as e:
            logger.error(f"Error applying parameter change: {e}")
            return f"Error applying change: {str(e)}"
    
    async def get_user_context(self, user_id: str = "default_user") -> str:
        """
        Retrieve all stored context for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            Formatted context summary
        """
        try:
            messages = [{"role": "user", "content": f"Retrieve all stored memories/context for user {user_id}"}]
            result = await self.agent.ainvoke({"messages": messages})
            
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "No context found."
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return f"Error: {str(e)}"


# Global instance
_personality_enhancer: Optional[PersonalityEnhancerAgent] = None


def create_personality_enhancer() -> PersonalityEnhancerAgent:
    """Get or create the personality enhancer agent."""
    global _personality_enhancer
    if _personality_enhancer is None:
        _personality_enhancer = PersonalityEnhancerAgent()
    return _personality_enhancer


def get_personality_enhancer() -> PersonalityEnhancerAgent:
    """Get the personality enhancer instance (creates if needed)."""
    return create_personality_enhancer()

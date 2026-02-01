"""
Zero Me - Personality Enhancer Agent
Manages memory, analytics, and parameter optimization
Using LangChain with Gemini models

This agent:
1. Observes all conversations between user and voice agent
2. Extracts and stores personal context in memory
3. Tracks analytics (questions asked, topics, engagement)
4. Logs everything to WandB for continual learning monitoring
5. Can dynamically modify agent parameters based on observed patterns
6. Prepares the system for the next session on session end
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

from parameters import (
    PERSONALITY_ENHANCER_CONFIG, 
    PERSONALITY_ENHANCER_SYSTEM_PROMPT,
    get_all_parameters,
    update_parameter,
)
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
    1. Observe all conversations and extract personal context
    2. Store context in Redis memory
    3. Track conversation analytics (questions, topics, engagement)
    4. Log everything to WandB for monitoring
    5. Dynamically modify parameters based on patterns
    6. Process session end and prepare for next session
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
            "user_sentiment": "neutral",  # Track overall sentiment
            "task_success_rate": 1.0,  # Track task success
        }
        
        # Track patterns across sessions
        self.session_count = 0
        self.total_questions_asked = 0
        self.total_tasks_delegated = 0
        
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
    
    @property
    def topics(self) -> List[str]:
        """Get the current conversation topics."""
        return self.current_conversation.get("topics", [])
    
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
            "user_sentiment": "neutral",
            "task_success_rate": 1.0,
        }
        self.session_count += 1
        logger.info("New conversation started")
        
        # Log session start to WandB
        if self.analytics:
            self.analytics.log_session_start(self.session_count)
    
    def record_question(self):
        """Record that the voice agent asked a question."""
        self.current_conversation["questions_asked"] += 1
        self.total_questions_asked += 1
    
    def record_task_delegation(self):
        """Record that a task was delegated to a sub-agent."""
        self.current_conversation["tasks_delegated"] += 1
        self.total_tasks_delegated += 1
    
    def record_topic(self, topic: str):
        """Record a conversation topic."""
        if topic and topic not in self.current_conversation["topics"]:
            self.current_conversation["topics"].append(topic)
    
    def record_task_result(self, success: bool):
        """Record if a task succeeded or failed."""
        current_rate = self.current_conversation["task_success_rate"]
        total_tasks = self.current_conversation["tasks_delegated"]
        if total_tasks > 0:
            # Rolling average
            self.current_conversation["task_success_rate"] = (
                (current_rate * (total_tasks - 1) + (1.0 if success else 0.0)) / total_tasks
            )
    
    async def end_conversation(self, user_id: str = "default_user") -> str:
        """
        End the current conversation and process everything.
        
        This method:
        1. Calculates conversation duration
        2. Logs all analytics to WandB
        3. Stores conversation summary in memory
        4. Analyzes patterns and suggests parameter updates
        5. Prepares system for next session
        
        Args:
            user_id: User identifier
        
        Returns:
            Summary of conversation analytics
        """
        if not self.current_conversation["start_time"]:
            return "No active conversation to end."
        
        logger.info("=" * 50)
        logger.info("🧠 PERSONALITY ENHANCER: Processing session end...")
        logger.info("=" * 50)
        
        # Calculate duration
        end_time = datetime.utcnow()
        duration = (end_time - self.current_conversation["start_time"]).total_seconds()
        
        # 1. Log all metrics to WandB
        try:
            self._log_session_to_wandb(user_id, duration)
            logger.info("✅ Logged session metrics to WandB")
        except Exception as e:
            logger.error(f"❌ WandB logging failed: {e}")
        
        # 2. Store conversation summary in memory
        try:
            summary_data = {
                "topic": ", ".join(self.current_conversation["topics"]) or "General conversation",
                "questions_asked": self.current_conversation["questions_asked"],
                "tasks_delegated": self.current_conversation["tasks_delegated"],
                "duration_seconds": duration,
                "task_success_rate": self.current_conversation["task_success_rate"],
                "timestamp": end_time.isoformat(),
            }
            if self.memory.is_available():
                self.memory.store_conversation_summary(user_id, summary_data)
                logger.info("✅ Stored conversation summary in memory")
        except Exception as e:
            logger.error(f"❌ Memory storage failed: {e}")
        
        # 3. Check if parameter updates are needed
        try:
            await self._check_and_update_parameters()
            logger.info("✅ Parameter check completed")
        except Exception as e:
            logger.error(f"❌ Parameter check failed: {e}")
        
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
            "user_sentiment": "neutral",
            "task_success_rate": 1.0,
        }
        
        logger.info("🏁 Session processing complete - Ready for next conversation")
        return result
    
    def _log_session_to_wandb(self, user_id: str, duration: float):
        """Log all session metrics to WandB."""
        if not self.analytics:
            return
        
        # Log basic conversation metrics
        self.analytics.log_conversation_end(
            user_id=user_id,
            questions_asked=self.current_conversation["questions_asked"],
            tasks_delegated=self.current_conversation["tasks_delegated"],
            duration_seconds=duration,
            topics=self.current_conversation["topics"],
        )
        
        # Log additional metrics
        self.analytics.log_custom_metric("session/questions_asked", self.current_conversation["questions_asked"])
        self.analytics.log_custom_metric("session/tasks_delegated", self.current_conversation["tasks_delegated"])
        self.analytics.log_custom_metric("session/duration_seconds", duration)
        self.analytics.log_custom_metric("session/task_success_rate", self.current_conversation["task_success_rate"])
        
        # Log cumulative metrics
        self.analytics.log_custom_metric("cumulative/total_sessions", self.session_count)
        self.analytics.log_custom_metric("cumulative/total_questions", self.total_questions_asked)
        self.analytics.log_custom_metric("cumulative/total_tasks", self.total_tasks_delegated)
        
        # Log topics as a table
        if self.current_conversation["topics"]:
            self.analytics.log_topics(self.current_conversation["topics"])
    
    async def _check_and_update_parameters(self):
        """
        Check if any parameters should be updated based on observed patterns.
        
        This implements a simple auto-tuning mechanism:
        - If task success rate is low, increase agent temperature slightly
        - If user asks many questions, the agent might be too brief
        - Track patterns and suggest prompt improvements
        """
        # Only auto-tune after enough sessions
        if self.session_count < 3:
            logger.info("Not enough sessions for auto-tuning yet")
            return
        
        task_success = self.current_conversation["task_success_rate"]
        questions_asked = self.current_conversation["questions_asked"]
        tasks_delegated = self.current_conversation["tasks_delegated"]
        
        # Pattern: Low task success rate
        if task_success < 0.7 and tasks_delegated > 0:
            logger.warning(f"Low task success rate: {task_success:.2f}")
            self.analytics.log_parameter_observation(
                "task_success_rate",
                task_success,
                "Low success rate detected - may need prompt refinement"
            )
        
        # Pattern: Many questions per task (user might be confused)
        if tasks_delegated > 0:
            questions_per_task = questions_asked / tasks_delegated
            if questions_per_task > 5:
                logger.warning(f"High questions per task: {questions_per_task:.1f}")
                self.analytics.log_parameter_observation(
                    "questions_per_task",
                    questions_per_task,
                    "High clarification rate - agent responses may need to be clearer"
                )
        
        # Log current parameters to WandB for tracking
        current_params = get_all_parameters()
        self.analytics.log_parameters_snapshot(current_params)
    
    async def analyze_and_store_context(
        self,
        conversation_text: str,
        user_id: str = "default_user",
    ) -> str:
        """
        Analyze a conversation and extract personal context to store.
        
        This is called after each conversation to learn about the user.
        The agent will:
        1. Extract personal preferences, habits, names, etc.
        2. Store them in Redis memory
        3. Log what was learned to WandB
        
        Args:
            conversation_text: The full conversation text
            user_id: User identifier
        
        Returns:
            Summary of what was learned and stored
        """
        try:
            logger.info("🔍 Analyzing conversation for personal context...")
            
            prompt = f"""
Analyze this conversation and extract any personal context worth remembering:

{conversation_text}

For each piece of useful context you find:
1. Use the store_memory tool to save it with a clear key like:
   - "preferred_name" (how the user likes to be called)
   - "work_info" (job, company, projects)
   - "schedule_preference" (morning person, night owl, etc.)
   - "communication_style" (formal, casual, brief, detailed)
   - "interests" (hobbies, topics they enjoy)
   - Any other relevant personal info

2. After storing, log what you learned using log_metric tool

IMPORTANT:
- Only store genuinely useful context
- Don't store sensitive info (passwords, financial)
- Use descriptive keys
- Store even small preferences (coffee preference, favorite color, etc.)

After storing everything, provide a brief summary of what you learned about the user.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.agent.ainvoke({"messages": messages})
            
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
            if ai_messages:
                learned = ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
                logger.info(f"📚 Learned: {learned[:200]}...")
                return learned
            return "Analysis completed."
            
        except Exception as e:
            logger.error(f"Error analyzing conversation: {e}")
            return f"Error analyzing conversation: {str(e)}"
    
    async def update_agent_personality(
        self,
        agent_name: str,
        observation: str,
        suggested_change: str,
    ) -> str:
        """
        Update an agent's personality/parameters based on observations.
        
        Args:
            agent_name: Which agent to update (voice_agent, doc_agent, etc.)
            observation: What was observed that prompted this change
            suggested_change: The suggested modification
        
        Returns:
            Result of the update
        """
        try:
            prompt = f"""
Based on this observation about the {agent_name}:

Observation: {observation}
Suggested Change: {suggested_change}

1. First use get_current_parameters to see current values
2. Decide if the change is appropriate
3. If yes, use modify_agent_parameter to make the change
4. Use log_parameter_change to record what was changed and why

Be conservative - only make changes that are clearly beneficial.
"""
            
            messages = [{"role": "user", "content": prompt}]
            result = await self.agent.ainvoke({"messages": messages})
            
            ai_messages = [m for m in result.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
            if ai_messages:
                return ai_messages[-1].content if hasattr(ai_messages[-1], "content") else str(ai_messages[-1])
            return "Update processed."
            
        except Exception as e:
            logger.error(f"Error updating personality: {e}")
            return f"Error: {str(e)}"
    
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
Then use log_parameter_change to record what was changed.
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

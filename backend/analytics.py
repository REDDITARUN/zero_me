"""
Zero Me - WandB Analytics Manager with Weave LLM Tracing
Tracks parameter changes, question counts, and memory changes for continual learning

All logging happens automatically when:
1. A session starts
2. A conversation ends
3. Parameters change
4. Memory operations occur
5. Agent calls complete

Weave provides detailed tracing of:
- LLM calls (inputs, outputs, latency, tokens)
- Tool executions
- Agent workflows
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger

try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    logger.warning("wandb not installed. Analytics features will be disabled.")

try:
    import weave
    WEAVE_AVAILABLE = True
except ImportError:
    WEAVE_AVAILABLE = False
    logger.warning("weave not installed. LLM tracing will be disabled.")

from parameters import get_all_parameters, ANALYTICS_CONFIG


class AnalyticsManager:
    """
    Manages WandB logging and Weave tracing for continual learning monitoring.
    
    Tracks:
    - Parameter changes (prompts, temperatures, etc.)
    - Question counts per conversation
    - Memory/context changes
    - Model performance metrics
    - Session metrics
    - Topics and conversation patterns
    
    Weave Tracing:
    - LLM call inputs and outputs
    - Tool execution traces
    - Agent workflow visualization
    """
    
    def __init__(self):
        """Initialize WandB and Weave connections."""
        self.enabled = WANDB_AVAILABLE and ANALYTICS_CONFIG["track_parameters"]
        self.weave_enabled = WEAVE_AVAILABLE
        self.run: Optional[wandb.Run] = None
        self.session_metrics: Dict[str, Any] = {
            "total_conversations": 0,
            "total_questions_asked": 0,
            "total_tasks_delegated": 0,
            "parameter_changes": 0,
            "memory_stores": 0,
            "session_start_time": None,
        }
        
        if self.enabled:
            self._init_wandb()
        
        if self.weave_enabled:
            self._init_weave()
    
    def _init_wandb(self):
        """Initialize WandB run."""
        try:
            api_key = os.getenv("WANDB_API_KEY")
            project = os.getenv("WANDB_PROJECT", ANALYTICS_CONFIG["wandb_project"])
            
            if not api_key:
                logger.warning("WANDB_API_KEY not found. Analytics disabled.")
                self.enabled = False
                return
            
            # Initialize WandB
            self.run = wandb.init(
                entity=os.getenv("WANDB_ENTITY", None),
                project=project,
                config=get_all_parameters(),
                name=f"zero_me_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                tags=["voice-agent", "multi-agent", "continual-learning"],
                reinit=True,
            )
            
            logger.info(f"WandB initialized: {self.run.url}")
        except Exception as e:
            logger.error(f"Failed to initialize WandB: {e}")
            self.enabled = False
    
    def _init_weave(self):
        """Initialize Weave for LLM tracing."""
        try:
            api_key = os.getenv("WANDB_API_KEY")
            entity = os.getenv("WANDB_ENTITY")
            project = os.getenv("WANDB_PROJECT", ANALYTICS_CONFIG["wandb_project"])
            
            if not api_key:
                logger.warning("WANDB_API_KEY not found. Weave tracing disabled.")
                self.weave_enabled = False
                return
            
            # Initialize Weave with the same project
            # Format: entity/project or just project
            weave_project = f"{entity}/{project}" if entity else project
            weave.init(weave_project)
            
            logger.info(f"Weave initialized for project: {weave_project}")
            logger.info("📊 View Weave traces at: https://wandb.ai/weave")
        except Exception as e:
            logger.error(f"Failed to initialize Weave: {e}")
            self.weave_enabled = False
    
    def log_session_start(self, session_number: int):
        """Log the start of a new session."""
        self.session_metrics["session_start_time"] = datetime.utcnow()
        
        if not self.enabled or not self.run:
            return
        
        try:
            wandb.log({
                "session/number": session_number,
                "session/started_at": datetime.utcnow().isoformat(),
            })
            logger.info(f"Session {session_number} start logged to WandB")
        except Exception as e:
            logger.error(f"Failed to log session start: {e}")
    
    def log_metric(self, name: str, value: float, step: Optional[int] = None):
        """
        Log a single metric to WandB.
        
        Args:
            name: Metric name (e.g., "questions_asked", "response_time")
            value: Metric value
            step: Optional step number
        """
        if not self.enabled or not self.run:
            return
            
        try:
            wandb.log({name: value}, step=step)
        except Exception as e:
            logger.error(f"Failed to log metric {name}: {e}")
    
    def log_custom_metric(self, name: str, value: Any):
        """Log a custom metric (alias for log_metric)."""
        if not self.enabled or not self.run:
            return
        
        try:
            wandb.log({name: value})
        except Exception as e:
            logger.error(f"Failed to log custom metric {name}: {e}")
    
    def log_metrics(self, metrics: Dict[str, Any], step: Optional[int] = None):
        """Log multiple metrics at once."""
        if not self.enabled or not self.run:
            return
            
        try:
            wandb.log(metrics, step=step)
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
    
    def log_conversation_end(
        self,
        user_id: str = None,
        questions_asked: int = 0,
        tasks_delegated: int = 0,
        duration_seconds: float = 0,
        topics: List[str] = None,
        conversation_id: str = None,
        summary: str = None,
    ):
        """
        Log metrics at the end of a conversation.
        
        Args:
            user_id: User identifier (anonymized)
            questions_asked: Number of questions the bot asked
            tasks_delegated: Number of tasks sent to sub-agents
            duration_seconds: Conversation duration
            topics: Main topics discussed
            conversation_id: Unique conversation ID
            summary: Conversation summary text
        """
        topics = topics or []
        
        self.session_metrics["total_conversations"] += 1
        self.session_metrics["total_questions_asked"] += questions_asked
        self.session_metrics["total_tasks_delegated"] += tasks_delegated
        
        if not self.enabled or not self.run:
            logger.info(f"WandB disabled - Conversation metrics: questions={questions_asked}, tasks={tasks_delegated}")
            return
        
        try:
            metrics = {
                "conversation/questions_asked": questions_asked,
                "conversation/tasks_delegated": tasks_delegated,
                "conversation/duration_seconds": duration_seconds,
                "conversation/topics_count": len(topics),
                "session/total_conversations": self.session_metrics["total_conversations"],
            }
            
            if self.session_metrics["total_conversations"] > 0:
                metrics["session/avg_questions_per_convo"] = (
                    self.session_metrics["total_questions_asked"] / 
                    self.session_metrics["total_conversations"]
                )
            
            wandb.log(metrics)
            logger.info(f"Conversation end logged to WandB: {metrics}")
                
        except Exception as e:
            logger.error(f"Failed to log conversation end: {e}")
    
    def log_topics(self, topics: List[str]):
        """Log conversation topics as a WandB table."""
        if not self.enabled or not self.run:
            return
        
        try:
            topic_table = wandb.Table(columns=["topic", "conversation_id"])
            for topic in topics:
                topic_table.add_data(topic, self.session_metrics["total_conversations"])
            wandb.log({"conversation/topics": topic_table})
        except Exception as e:
            logger.error(f"Failed to log topics: {e}")
    
    def log_parameter_change(
        self,
        agent_name: str,
        param_key: str,
        old_value: Any,
        new_value: Any,
        reason: str,
    ):
        """
        Log a parameter change for continual learning tracking.
        
        Args:
            agent_name: Name of the agent whose parameter changed
            param_key: Parameter key that changed
            old_value: Previous value
            new_value: New value
            reason: Why the change was made
        """
        self.session_metrics["parameter_changes"] += 1
        
        if not self.enabled or not self.run:
            logger.info(f"WandB disabled - Parameter change: {agent_name}.{param_key}: {old_value} -> {new_value}")
            return
        
        try:
            wandb.log({
                "parameter_change/agent": agent_name,
                "parameter_change/key": param_key,
                "parameter_change/reason": reason,
                "session/total_parameter_changes": self.session_metrics["parameter_changes"],
            })
            
            # Update config
            wandb.config.update({
                f"{agent_name}/{param_key}": new_value
            }, allow_val_change=True)
            
            logger.info(f"Parameter change logged: {agent_name}.{param_key}: {old_value} -> {new_value}")
        except Exception as e:
            logger.error(f"Failed to log parameter change: {e}")
    
    def log_parameter_observation(
        self,
        metric_name: str,
        value: Any,
        observation: str,
    ):
        """Log an observation about parameters that might need adjustment."""
        if not self.enabled or not self.run:
            logger.info(f"WandB disabled - Parameter observation: {metric_name}={value} - {observation}")
            return
        
        try:
            wandb.log({
                f"observation/{metric_name}": value,
            })
            
            # Log observation as an alert
            wandb.alert(
                title=f"Parameter Observation: {metric_name}",
                text=f"{observation}\nValue: {value}",
                level=wandb.AlertLevel.INFO,
            )
        except Exception as e:
            logger.error(f"Failed to log parameter observation: {e}")
    
    def log_parameters_snapshot(self, parameters: Dict[str, Any]):
        """Log a snapshot of all current parameters."""
        if not self.enabled or not self.run:
            return
        
        try:
            wandb.config.update(parameters, allow_val_change=True)
            logger.debug("Parameters snapshot logged to WandB")
        except Exception as e:
            logger.error(f"Failed to log parameters snapshot: {e}")
    
    def log_memory_operation(
        self,
        operation: str,  # "store", "retrieve", "delete"
        user_id: str,
        context_key: str,
        success: bool,
    ):
        """
        Log a memory operation.
        
        Args:
            operation: Type of operation
            user_id: User identifier
            context_key: Context key involved
            success: Whether operation succeeded
        """
        if operation == "store" and success:
            self.session_metrics["memory_stores"] += 1
        
        if not self.enabled or not self.run:
            return
        
        try:
            wandb.log({
                f"memory/{operation}_success": 1 if success else 0,
                "session/total_memory_stores": self.session_metrics["memory_stores"],
            })
        except Exception as e:
            logger.error(f"Failed to log memory operation: {e}")
    
    def log_agent_call(
        self,
        agent_name: str,
        task_type: str,
        success: bool,
        response_time_ms: float,
    ):
        """
        Log a sub-agent call.
        
        Args:
            agent_name: Name of the agent called
            task_type: Type of task (e.g., "add_todo", "send_email")
            success: Whether the call succeeded
            response_time_ms: Response time in milliseconds
        """
        if not self.enabled or not self.run:
            return
        
        try:
            wandb.log({
                f"agent/{agent_name}/calls": 1,
                f"agent/{agent_name}/success_rate": 1 if success else 0,
                f"agent/{agent_name}/response_time_ms": response_time_ms,
                f"agent/{agent_name}/task_type": task_type,
            })
        except Exception as e:
            logger.error(f"Failed to log agent call: {e}")
    
    def finish(self):
        """Finish the WandB run and upload final metrics."""
        if not self.enabled or not self.run:
            logger.info("WandB run finished (was disabled)")
            return
        
        try:
            # Log final session summary
            wandb.log({
                "session/final_total_conversations": self.session_metrics["total_conversations"],
                "session/final_total_questions": self.session_metrics["total_questions_asked"],
                "session/final_total_tasks": self.session_metrics["total_tasks_delegated"],
                "session/final_parameter_changes": self.session_metrics["parameter_changes"],
                "session/final_memory_stores": self.session_metrics["memory_stores"],
            })
            
            wandb.finish()
            logger.info("WandB run finished successfully")
        except Exception as e:
            logger.error(f"Failed to finish WandB run: {e}")


# ============================================
# WEAVE TRACING DECORATORS & HELPERS
# ============================================

def weave_op(func):
    """
    Decorator to trace a function with Weave.
    Use this on any function you want to track in Weave.
    
    Example:
        @weave_op
        def my_llm_call(prompt):
            return llm.generate(prompt)
    """
    if WEAVE_AVAILABLE:
        return weave.op()(func)
    return func


def trace_llm_call(model: str, prompt: str, response: str, metadata: Dict[str, Any] = None):
    """
    Manually trace an LLM call to Weave.
    Use this for LLM calls that aren't automatically traced.
    
    Args:
        model: Model name (e.g., "gemini-3-flash-preview")
        prompt: Input prompt
        response: Model response
        metadata: Additional metadata (tokens, latency, etc.)
    """
    if not WEAVE_AVAILABLE:
        return
    
    try:
        @weave.op()
        def _traced_llm_call(model_name: str, input_prompt: str) -> str:
            return response
        
        # This creates a trace entry
        _traced_llm_call(model, prompt)
    except Exception as e:
        logger.debug(f"Weave trace failed: {e}")


def trace_tool_call(tool_name: str, inputs: Dict[str, Any], output: str, success: bool = True):
    """
    Manually trace a tool call to Weave.
    
    Args:
        tool_name: Name of the tool
        inputs: Tool input parameters
        output: Tool output
        success: Whether the call succeeded
    """
    if not WEAVE_AVAILABLE:
        return
    
    try:
        @weave.op()
        def _traced_tool(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            return {"output": output, "success": success}
        
        _traced_tool(tool_name, inputs)
    except Exception as e:
        logger.debug(f"Weave tool trace failed: {e}")


def trace_agent_delegation(
    from_agent: str,
    to_agent: str,
    task: str,
    result: str,
    duration_ms: float,
):
    """
    Trace an agent delegation event.
    
    Args:
        from_agent: Source agent
        to_agent: Target agent
        task: Task description
        result: Task result
        duration_ms: Execution time in milliseconds
    """
    if not WEAVE_AVAILABLE:
        return
    
    try:
        @weave.op()
        def _agent_delegation(source: str, target: str, task_desc: str) -> Dict[str, Any]:
            return {
                "result": result,
                "duration_ms": duration_ms,
            }
        
        _agent_delegation(from_agent, to_agent, task)
    except Exception as e:
        logger.debug(f"Weave delegation trace failed: {e}")


# Global instance
_analytics_manager: Optional[AnalyticsManager] = None


def get_analytics_manager() -> AnalyticsManager:
    """Get or create the global analytics manager instance."""
    global _analytics_manager
    if _analytics_manager is None:
        _analytics_manager = AnalyticsManager()
    return _analytics_manager

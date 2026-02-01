"""
Zero Me - Analytics Tools
LangChain tools for WandB logging and parameter management
"""

import os
from typing import Any, Optional
from langchain.tools import tool
from loguru import logger

# Import from parent directory
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import get_analytics_manager
from parameters import update_parameter, get_all_parameters


@tool
def log_metric(metric_name: str, value: float) -> str:
    """
    Log a metric to WandB for monitoring.
    
    Args:
        metric_name: Name of the metric (e.g., "response_quality", "user_satisfaction")
        value: Numeric value of the metric
    
    Returns:
        Confirmation message
    """
    analytics = get_analytics_manager()
    
    analytics.log_metric(metric_name, value)
    
    return f"Logged metric: {metric_name} = {value}"


@tool
def log_question_count(count: int, conversation_topic: str) -> str:
    """
    Log how many questions were asked in a conversation.
    This helps track if we're asking too many questions.
    
    Args:
        count: Number of questions asked
        conversation_topic: Main topic of the conversation
    
    Returns:
        Confirmation with analysis
    """
    analytics = get_analytics_manager()
    
    analytics.log_metric("questions_per_conversation", count)
    
    # Provide feedback based on count
    if count == 0:
        feedback = "No questions asked - the user's request was clear."
    elif count <= 2:
        feedback = "Reasonable number of clarifying questions."
    elif count <= 4:
        feedback = "Multiple questions asked - consider if some could be inferred."
    else:
        feedback = "Many questions asked - this might indicate unclear prompts or need for better context retention."
    
    logger.info(f"Conversation '{conversation_topic}' had {count} questions")
    
    return f"Logged {count} questions for '{conversation_topic}'. Analysis: {feedback}"


@tool
def log_parameter_change(
    agent_name: str,
    parameter_key: str,
    old_value: str,
    new_value: str,
    reason: str,
) -> str:
    """
    Log a parameter change for continual learning tracking.
    
    Args:
        agent_name: Name of the agent (e.g., "voice_agent", "todo_agent")
        parameter_key: The parameter being changed (e.g., "temperature", "max_tokens")
        old_value: Previous value
        new_value: New value
        reason: Why the change was made
    
    Returns:
        Confirmation message
    """
    analytics = get_analytics_manager()
    
    analytics.log_parameter_change(
        agent_name=agent_name,
        param_key=parameter_key,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    
    return f"Logged parameter change: {agent_name}.{parameter_key} changed from '{old_value}' to '{new_value}'. Reason: {reason}"


@tool
def modify_agent_parameter(
    agent_name: str,
    parameter_key: str,
    new_value: str,
    reason: str,
) -> str:
    """
    Modify an agent's parameter and log the change.
    
    This allows the personality enhancer to adjust agent behavior
    based on observed patterns.
    
    Args:
        agent_name: Name of the agent to modify (e.g., "voice_agent", "main_agent")
        parameter_key: Parameter to change (e.g., "temperature")
        new_value: New value for the parameter
        reason: Reason for the change
    
    Returns:
        Success or error message
    """
    analytics = get_analytics_manager()
    
    # Get current parameters to find old value
    all_params = get_all_parameters()
    agent_config = all_params.get(agent_name, {}).get("config", {})
    old_value = agent_config.get(parameter_key, "unknown")
    
    # Try to convert new_value to appropriate type
    try:
        if parameter_key == "temperature":
            typed_value = float(new_value)
        elif parameter_key == "max_tokens":
            typed_value = int(new_value)
        else:
            typed_value = new_value
    except ValueError:
        typed_value = new_value
    
    # Update the parameter
    success = update_parameter(agent_name, parameter_key, typed_value)
    
    if success:
        # Log the change
        analytics.log_parameter_change(
            agent_name=agent_name,
            param_key=parameter_key,
            old_value=old_value,
            new_value=typed_value,
            reason=reason,
        )
        
        logger.info(f"Modified {agent_name}.{parameter_key}: {old_value} -> {typed_value}")
        return f"Successfully modified {agent_name}.{parameter_key} from {old_value} to {typed_value}. Reason: {reason}"
    else:
        return f"Failed to modify parameter. Agent '{agent_name}' or parameter '{parameter_key}' may not exist."


@tool
def get_current_parameters(agent_name: Optional[str] = None) -> str:
    """
    Get current parameter values for agents.
    
    Args:
        agent_name: Specific agent name, or None for all agents
    
    Returns:
        Formatted parameter information
    """
    all_params = get_all_parameters()
    
    if agent_name:
        if agent_name not in all_params:
            return f"Agent '{agent_name}' not found. Available: {', '.join(all_params.keys())}"
        
        params = all_params[agent_name]
        config = params.get("config", {})
        
        lines = [f"Parameters for {agent_name}:"]
        for key, value in config.items():
            lines.append(f"  - {key}: {value}")
        lines.append(f"  - prompt_length: {params.get('prompt_length', 0)} chars")
        
        return "\n".join(lines)
    else:
        lines = ["All agent parameters:"]
        for name, params in all_params.items():
            config = params.get("config", {})
            lines.append(f"\n{name}:")
            for key, value in config.items():
                lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines)


@tool
def record_conversation_analytics(
    questions_asked: int,
    tasks_delegated: int,
    duration_seconds: float,
    topics: str,
    user_id: str = "default_user",
) -> str:
    """
    Record analytics at the end of a conversation.
    
    Args:
        questions_asked: Number of questions the bot asked
        tasks_delegated: Number of tasks sent to sub-agents
        duration_seconds: How long the conversation lasted
        topics: Comma-separated list of main topics discussed
        user_id: User identifier
    
    Returns:
        Confirmation message
    """
    analytics = get_analytics_manager()
    
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    
    analytics.log_conversation_end(
        user_id=user_id,
        questions_asked=questions_asked,
        tasks_delegated=tasks_delegated,
        duration_seconds=duration_seconds,
        topics=topic_list,
    )
    
    return f"Recorded conversation: {questions_asked} questions, {tasks_delegated} tasks, {duration_seconds:.1f}s, topics: {topics}"

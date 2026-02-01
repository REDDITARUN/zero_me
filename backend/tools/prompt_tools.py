"""
Zero Me - Prompt Modification Tools
Tools for the Personality Enhancer to modify agent prompts dynamically
"""

import os
import sys
from typing import Optional
from langchain.tools import tool
from loguru import logger

# Import colorful logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logging_utils import log_tool_call, log_tool_result

# Import parameters module
import parameters


@tool
def get_agent_prompt(agent_name: str) -> str:
    """
    Get the current system prompt for a specific agent.
    
    Args:
        agent_name: One of: voice_agent, main_agent, doc_agent, todo_agent, 
                    email_agent, calendar_agent, personality_enhancer
    
    Returns:
        The current system prompt for the agent
    """
    log_tool_call("get_agent_prompt", {"agent_name": agent_name})
    
    prompt_map = {
        "voice_agent": parameters.VOICE_AGENT_SYSTEM_PROMPT,
        "main_agent": parameters.MAIN_AGENT_SYSTEM_PROMPT,
        "doc_agent": parameters.DOC_AGENT_SYSTEM_PROMPT,
        "todo_agent": parameters.TODO_AGENT_SYSTEM_PROMPT,
        "email_agent": parameters.EMAIL_AGENT_SYSTEM_PROMPT,
        "calendar_agent": parameters.CALENDAR_AGENT_SYSTEM_PROMPT,
        "personality_enhancer": parameters.PERSONALITY_ENHANCER_SYSTEM_PROMPT,
    }
    
    if agent_name not in prompt_map:
        result = f"Error: Unknown agent '{agent_name}'. Valid agents: {list(prompt_map.keys())}"
        log_tool_result("get_agent_prompt", result, success=False)
        return result
    
    result = prompt_map[agent_name]
    log_tool_result("get_agent_prompt", f"Retrieved {agent_name} prompt ({len(result)} chars)")
    return result


@tool
def update_agent_prompt(
    agent_name: str,
    new_prompt: str,
    reason: str,
) -> str:
    """
    Update the system prompt for a specific agent.
    This change persists in memory and will be used for new conversations.
    
    Use this to improve agent behavior based on conversation analytics.
    Common improvements:
    - Reduce questions by adding context awareness
    - Improve memory usage by reminding to check memory first
    - Add domain-specific knowledge from user preferences
    
    Args:
        agent_name: One of: voice_agent, main_agent, doc_agent, todo_agent,
                    email_agent, calendar_agent, personality_enhancer
        new_prompt: The complete new system prompt
        reason: Why this change is being made (logged to WandB)
    
    Returns:
        Success or error message
    """
    log_tool_call("update_agent_prompt", {
        "agent_name": agent_name, 
        "prompt_length": len(new_prompt),
        "reason": reason[:50]
    })
    
    valid_agents = [
        "voice_agent", "main_agent", "doc_agent", "todo_agent",
        "email_agent", "calendar_agent", "personality_enhancer"
    ]
    
    if agent_name not in valid_agents:
        result = f"Error: Unknown agent '{agent_name}'. Valid agents: {valid_agents}"
        log_tool_result("update_agent_prompt", result, success=False)
        return result
    
    if len(new_prompt) < 100:
        result = "Error: Prompt too short. Prompts should be at least 100 characters."
        log_tool_result("update_agent_prompt", result, success=False)
        return result
    
    if len(new_prompt) > 10000:
        result = "Error: Prompt too long. Prompts should be under 10000 characters."
        log_tool_result("update_agent_prompt", result, success=False)
        return result
    
    try:
        # Update the prompt in parameters module
        old_prompt = getattr(parameters, f"{agent_name.upper()}_SYSTEM_PROMPT")
        setattr(parameters, f"{agent_name.upper()}_SYSTEM_PROMPT", new_prompt)
        
        # Log to WandB
        try:
            from analytics import get_analytics_manager
            analytics = get_analytics_manager()
            analytics.log_parameter_change(
                agent_name=agent_name,
                parameter_key="system_prompt",
                old_value=f"[{len(old_prompt)} chars]",
                new_value=f"[{len(new_prompt)} chars]",
                reason=reason
            )
        except Exception as e:
            logger.warning(f"Could not log to WandB: {e}")
        
        result = f"Successfully updated {agent_name} prompt. New length: {len(new_prompt)} chars. Reason: {reason}"
        log_tool_result("update_agent_prompt", result)
        return result
        
    except Exception as e:
        result = f"Error updating prompt: {str(e)}"
        log_tool_result("update_agent_prompt", result, success=False)
        return result


@tool
def append_to_prompt(
    agent_name: str,
    section_title: str,
    content: str,
    reason: str,
) -> str:
    """
    Append a new section to an agent's system prompt.
    This is safer than replacing the entire prompt.
    
    Use this to add:
    - User-specific context (e.g., "User prefers morning meetings")
    - Learned behaviors (e.g., "Always check memory before asking questions")
    - Domain knowledge from conversations
    
    Args:
        agent_name: The agent to modify
        section_title: Title for the new section (e.g., "# User Preferences")
        content: The content to add
        reason: Why this change is being made
    
    Returns:
        Success or error message
    """
    log_tool_call("append_to_prompt", {
        "agent_name": agent_name,
        "section_title": section_title,
        "content_length": len(content)
    })
    
    valid_agents = [
        "voice_agent", "main_agent", "doc_agent", "todo_agent",
        "email_agent", "calendar_agent", "personality_enhancer"
    ]
    
    if agent_name not in valid_agents:
        result = f"Error: Unknown agent '{agent_name}'"
        log_tool_result("append_to_prompt", result, success=False)
        return result
    
    try:
        current_prompt = getattr(parameters, f"{agent_name.upper()}_SYSTEM_PROMPT")
        
        # Check if section already exists
        if section_title in current_prompt:
            result = f"Section '{section_title}' already exists in {agent_name} prompt. Use update_agent_prompt to modify it."
            log_tool_result("append_to_prompt", result, success=False)
            return result
        
        # Append new section
        new_prompt = current_prompt + f"\n\n{section_title}\n{content}"
        setattr(parameters, f"{agent_name.upper()}_SYSTEM_PROMPT", new_prompt)
        
        # Log to WandB
        try:
            from analytics import get_analytics_manager
            analytics = get_analytics_manager()
            analytics.log_parameter_change(
                agent_name=agent_name,
                parameter_key="system_prompt",
                old_value=f"Added section: {section_title}",
                new_value=f"+{len(content)} chars",
                reason=reason
            )
        except Exception as e:
            logger.warning(f"Could not log to WandB: {e}")
        
        result = f"Successfully added '{section_title}' to {agent_name} prompt. Total length: {len(new_prompt)} chars."
        log_tool_result("append_to_prompt", result)
        return result
        
    except Exception as e:
        result = f"Error appending to prompt: {str(e)}"
        log_tool_result("append_to_prompt", result, success=False)
        return result


@tool
def get_all_agent_configs() -> str:
    """
    Get configuration for all agents including temperatures, models, etc.
    
    Returns:
        JSON-formatted string of all agent configurations
    """
    log_tool_call("get_all_agent_configs", {})
    
    import json
    configs = parameters.get_all_parameters()
    result = json.dumps(configs, indent=2)
    
    log_tool_result("get_all_agent_configs", f"Retrieved configs for {len(configs)} agents")
    return result


@tool
def update_agent_temperature(
    agent_name: str,
    new_temperature: float,
    reason: str,
) -> str:
    """
    Update the temperature setting for an agent.
    Lower temperatures (0.1-0.3) = more deterministic, focused responses
    Higher temperatures (0.7-0.9) = more creative, varied responses
    
    Args:
        agent_name: The agent to modify
        new_temperature: Value between 0.0 and 1.0
        reason: Why this change is being made
    
    Returns:
        Success or error message
    """
    log_tool_call("update_agent_temperature", {
        "agent_name": agent_name,
        "new_temperature": new_temperature,
        "reason": reason[:50]
    })
    
    if not 0.0 <= new_temperature <= 1.0:
        result = "Error: Temperature must be between 0.0 and 1.0"
        log_tool_result("update_agent_temperature", result, success=False)
        return result
    
    success = parameters.update_parameter(agent_name, "temperature", new_temperature)
    
    if success:
        # Log to WandB
        try:
            from analytics import get_analytics_manager
            analytics = get_analytics_manager()
            analytics.log_parameter_change(
                agent_name=agent_name,
                parameter_key="temperature",
                old_value="previous",
                new_value=str(new_temperature),
                reason=reason
            )
        except Exception as e:
            logger.warning(f"Could not log to WandB: {e}")
        
        result = f"Successfully updated {agent_name} temperature to {new_temperature}. Reason: {reason}"
        log_tool_result("update_agent_temperature", result)
        return result
    else:
        result = f"Error: Could not update temperature for '{agent_name}'"
        log_tool_result("update_agent_temperature", result, success=False)
        return result


@tool
def analyze_conversation_for_improvements(
    questions_asked: int,
    tasks_completed: int,
    memory_accesses: int,
    topics: str,
) -> str:
    """
    Analyze conversation metrics and suggest prompt improvements.
    
    Args:
        questions_asked: Number of questions the bot asked the user
        tasks_completed: Number of tasks successfully completed
        memory_accesses: Number of times memory was accessed
        topics: Comma-separated list of conversation topics
    
    Returns:
        Analysis and suggested improvements
    """
    log_tool_call("analyze_conversation_for_improvements", {
        "questions": questions_asked,
        "tasks": tasks_completed,
        "memory": memory_accesses,
        "topics": topics[:50]
    })
    
    suggestions = []
    
    # Analyze question frequency
    if questions_asked > 3 and tasks_completed < questions_asked / 2:
        suggestions.append(
            "- High question rate with low task completion. "
            "Consider adding context-awareness to prompts to reduce clarifying questions."
        )
    
    # Analyze memory usage
    if memory_accesses == 0 and questions_asked > 2:
        suggestions.append(
            "- No memory accesses despite multiple questions. "
            "Add instructions to check memory before asking the user."
        )
    
    # Analyze task efficiency
    if tasks_completed > 0 and questions_asked > tasks_completed * 2:
        suggestions.append(
            "- More than 2 questions per task. "
            "Consider making agents more proactive with reasonable defaults."
        )
    
    if not suggestions:
        suggestions.append(
            "- Conversation metrics look good! "
            "No major improvements suggested at this time."
        )
    
    result = f"""Conversation Analysis:
- Questions asked: {questions_asked}
- Tasks completed: {tasks_completed}
- Memory accesses: {memory_accesses}
- Topics: {topics}

Suggested Improvements:
{"".join(suggestions)}"""
    
    log_tool_result("analyze_conversation_for_improvements", "Analysis complete")
    return result

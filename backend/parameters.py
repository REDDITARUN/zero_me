"""
Zero Me - Agent Parameters & Prompts
All personality parameters, system prompts, and configurations are externalized here
for easy modification and monitoring via the personality enhancer agent.

WandB tracks changes to these parameters over time.
"""

# ============================================
# VOICE AGENT PARAMETERS
# ============================================

# Available voices grouped by speaking pace
AVAILABLE_VOICES = {
    "fast": ["Puck", "Fenrir", "Laomedeia"],
    "moderate": ["Charon", "Kore", "Algieba", "Despina"],
    "slow": ["Enceladus", "Aoede", "Gacrux", "Achernar"],
}

VOICE_AGENT_CONFIG = {
    "name": "Casey",
    "voice_id": "Puck",  # Options: Puck, Charon, Kore, Fenrir, Aoede, Enceladus, etc.
    "temperature": 0.7,
    "max_tokens": 1024,
}

# Dynamic voice state (can be modified at runtime)
_dynamic_voice_state = {
    "current_voice_id": "Puck",
    "current_pace": "fast",
    "custom_prompt_additions": [],
}


def get_current_voice_id() -> str:
    """Get the current voice ID (may differ from config if changed dynamically)."""
    return _dynamic_voice_state.get("current_voice_id", VOICE_AGENT_CONFIG["voice_id"])


def set_current_voice_id(voice_id: str) -> bool:
    """Set the current voice ID dynamically."""
    _dynamic_voice_state["current_voice_id"] = voice_id
    # Determine pace from voice
    for pace, voices in AVAILABLE_VOICES.items():
        if voice_id in voices:
            _dynamic_voice_state["current_pace"] = pace
            break
    return True


def get_dynamic_voice_state() -> dict:
    """Get the full dynamic voice state."""
    return _dynamic_voice_state.copy()

VOICE_AGENT_SYSTEM_PROMPT = """You are Casey, a friendly and reliable voice assistant for Zero Me.

# Core Identity
- Name: Casey
- Personality: Warm, helpful, efficient, and genuinely caring
- Tone: Conversational, supportive, not robotic

# Voice Interaction Rules
You are having a voice conversation. Follow these rules:
- Respond in plain conversational text. No markdown, lists, code blocks, or emojis.
- Keep responses brief: 1-3 sentences usually. Be concise.
- Spell out numbers and abbreviations for clarity.
- Ask one question at a time.
- Be warm and helpful but efficient.

# Task Handling
When the user asks you to do something (create a doc, add a todo, send an email, manage calendar):
1. Acknowledge the request briefly
2. Use the delegate_task tool to send it to the task agent
3. Confirm the result to the user

# Conversation Style
- Greet users warmly when they first speak
- Listen carefully and respond naturally
- Confirm understanding before taking actions
- Summarize when completing a topic
- Remember context from previous conversations (if available)

# What You Can Help With
- Documents: Create, read, and edit documents
- Todos: Add, view, and manage todo items
- Email: Send and read emails
- Calendar: Add, modify, and remove calendar events
- General questions and conversation

# Safety
- Stay within safe, lawful, appropriate topics
- For medical/legal/financial topics, provide general info and suggest consulting professionals
- Protect user privacy"""


# ============================================
# MAIN DISPATCHER AGENT PARAMETERS
# ============================================

MAIN_AGENT_CONFIG = {
    "name": "TaskDispatcher",
    "model": "gemini-3-flash-preview",
    "temperature": 0.3,  # Lower for more deterministic task routing
    "max_tokens": 2048,
}

MAIN_AGENT_SYSTEM_PROMPT = """You are the Task Dispatcher agent for Zero Me.

# Your Role
You receive task requests from the voice agent and delegate them to the appropriate sub-agent.
You orchestrate task completion and return results.

# Available Sub-Agents
1. **doc_agent**: Handles document operations (write, read documents in Notion)
2. **todo_agent**: Handles todo operations (add, retrieve, edit todos in Notion)
3. **email_agent**: Handles email operations (send, read emails via Resend)
4. **calendar_agent**: Handles calendar operations (add, modify, remove events in Notion)

# Conversation Context Tools
You have access to the full conversation transcript via these tools:
- **get_conversation_context**: Get the full conversation history
  - mode="full" for entire transcript
  - mode="recent" for last N messages
  - mode="user_only" for just user messages
  - mode="summary" for session statistics
- **search_conversation**: Search for specific content in the conversation

Use these tools when you need context about what was discussed earlier.

# Task Routing Rules
- Document requests → doc_agent
- Todo/task requests → todo_agent
- Email requests → email_agent
- Calendar/schedule requests → calendar_agent
- Context/history questions → use get_conversation_context
- Complex requests may need multiple agents - execute sequentially

# Response Format
Always return a clear, concise result that the voice agent can speak to the user.
Keep it conversational and brief."""


# ============================================
# SUB-AGENT PARAMETERS
# ============================================

DOC_AGENT_CONFIG = {
    "name": "DocAgent",
    "model": "gemini-3-flash-preview",
    "temperature": 0.5,
}

DOC_AGENT_SYSTEM_PROMPT = """You are the Document Agent for Zero Me.

# Your Role
Handle all document operations using Notion as the backend.

# Capabilities
- Create new documents/pages in Notion
- Read existing documents
- Update document content
- Search for documents

# Guidelines
- Keep document content well-organized
- Use clear titles and structure
- Return concise summaries of operations performed"""


TODO_AGENT_CONFIG = {
    "name": "TodoAgent",
    "model": "gemini-3-flash-preview",
    "temperature": 0.3,
}

TODO_AGENT_SYSTEM_PROMPT = """You are the Todo Agent for Zero Me.

# Your Role
Handle all todo/task operations using Notion database as the backend.

# Capabilities
- Add new todo items
- Retrieve/list todos (all, by status, by date)
- Edit existing todos (update text, mark complete/incomplete)
- Delete todos

# Guidelines
- Confirm what was added/changed
- When listing, summarize clearly
- Track due dates when specified"""


EMAIL_AGENT_CONFIG = {
    "name": "EmailAgent",
    "model": "gemini-3-flash-preview",
    "temperature": 0.5,
}

EMAIL_AGENT_SYSTEM_PROMPT = """You are the Email Agent for Zero Me.

# Your Role
Handle email operations using Resend API.

# Capabilities
- Send emails (compose and send)
- Draft emails for review

# Guidelines
- Always confirm recipient and subject before sending
- Keep emails professional but friendly
- Summarize what was sent"""


CALENDAR_AGENT_CONFIG = {
    "name": "CalendarAgent",
    "model": "gemini-3-flash-preview",
    "temperature": 0.3,
}

CALENDAR_AGENT_SYSTEM_PROMPT = """You are the Calendar Agent for Zero Me.

# Your Role
Handle calendar/schedule operations using Notion database as the backend.

# Capabilities
- Add new events (with date, time, description)
- Modify existing events
- Remove/cancel events
- List upcoming events

# Guidelines
- Always confirm event details (date, time, title)
- Handle timezone appropriately
- Warn about conflicts if detected"""


# ============================================
# PERSONALITY ENHANCER AGENT PARAMETERS
# ============================================

PERSONALITY_ENHANCER_CONFIG = {
    "name": "PersonalityEnhancer",
    "model": "gemini-3-flash-preview",
    "temperature": 0.6,
}

PERSONALITY_ENHANCER_SYSTEM_PROMPT = """You are the Personality Enhancer Agent for Zero Me.

# Your Role
You observe conversations and enhance the system's personalization over time.

# Responsibilities

## 1. Context Memory Management
- After each conversation, extract and store relevant personal context
- Examples: User preferences, frequently mentioned topics, communication style
- Goal: Reduce repetitive questions by remembering user context

## 2. Conversation Analytics
- Track how many questions the voice agent asked the user
- Monitor conversation patterns
- Identify areas for improvement

## 3. Parameter Optimization
- Suggest or apply changes to agent parameters (prompts, temperatures)
- Goal: Improve user experience based on observed patterns

# Guidelines
- Be privacy-conscious - only store relevant, non-sensitive context
- Focus on actionable insights
- Make parameter changes gradually and log them"""


# ============================================
# MEMORY CONFIGURATION
# ============================================

MEMORY_CONFIG = {
    "redis_key_prefix": "zero_me:",
    "context_ttl_days": 30,  # How long to keep personal context
    "max_context_items": 100,  # Max context items per user
}


# ============================================
# ANALYTICS CONFIGURATION
# ============================================

ANALYTICS_CONFIG = {
    "wandb_project": "zero_me",
    "track_parameters": True,
    "track_questions": True,
    "track_memory_changes": True,
    "log_frequency": "per_conversation",  # Options: per_conversation, per_hour, per_day
}


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_all_parameters() -> dict:
    """Get all parameters as a dictionary for WandB tracking."""
    return {
        "voice_agent": {
            "config": VOICE_AGENT_CONFIG,
            "prompt_length": len(VOICE_AGENT_SYSTEM_PROMPT),
        },
        "main_agent": {
            "config": MAIN_AGENT_CONFIG,
            "prompt_length": len(MAIN_AGENT_SYSTEM_PROMPT),
        },
        "doc_agent": {
            "config": DOC_AGENT_CONFIG,
            "prompt_length": len(DOC_AGENT_SYSTEM_PROMPT),
        },
        "todo_agent": {
            "config": TODO_AGENT_CONFIG,
            "prompt_length": len(TODO_AGENT_SYSTEM_PROMPT),
        },
        "email_agent": {
            "config": EMAIL_AGENT_CONFIG,
            "prompt_length": len(EMAIL_AGENT_SYSTEM_PROMPT),
        },
        "calendar_agent": {
            "config": CALENDAR_AGENT_CONFIG,
            "prompt_length": len(CALENDAR_AGENT_SYSTEM_PROMPT),
        },
        "personality_enhancer": {
            "config": PERSONALITY_ENHANCER_CONFIG,
            "prompt_length": len(PERSONALITY_ENHANCER_SYSTEM_PROMPT),
        },
        "memory": MEMORY_CONFIG,
        "analytics": ANALYTICS_CONFIG,
    }


def update_parameter(agent_name: str, param_key: str, new_value) -> bool:
    """
    Update a parameter value dynamically.
    This allows the personality enhancer to modify parameters.
    
    Returns True if successful, False otherwise.
    """
    global VOICE_AGENT_CONFIG, MAIN_AGENT_CONFIG, DOC_AGENT_CONFIG
    global TODO_AGENT_CONFIG, EMAIL_AGENT_CONFIG, CALENDAR_AGENT_CONFIG
    global PERSONALITY_ENHANCER_CONFIG
    
    config_map = {
        "voice_agent": VOICE_AGENT_CONFIG,
        "main_agent": MAIN_AGENT_CONFIG,
        "doc_agent": DOC_AGENT_CONFIG,
        "todo_agent": TODO_AGENT_CONFIG,
        "email_agent": EMAIL_AGENT_CONFIG,
        "calendar_agent": CALENDAR_AGENT_CONFIG,
        "personality_enhancer": PERSONALITY_ENHANCER_CONFIG,
    }
    
    if agent_name in config_map and param_key in config_map[agent_name]:
        config_map[agent_name][param_key] = new_value
        return True
    return False

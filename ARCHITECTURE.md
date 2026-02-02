git # Zero Me - Agent Architecture

## Overview

Zero Me is a multi-agent voice assistant system built with **Gemini LLMs** and **Pipecat**. The architecture follows a hierarchical delegation pattern where a voice agent routes tasks to specialized sub-agents.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER (Voice)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VOICE AGENT LAYER                                   │
│                    (Pipecat + Gemini Live)                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     GeminiLiveLLMService                              │  │
│  │  • Model: Gemini Live (native speech-to-speech)                       │  │
│  │  • Voice ID: Puck                                                     │  │
│  │  • Function: delegate_task                                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                          delegate_task(task, type)
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     VOICE-AGENT BRIDGE                                      │
│                    (VoiceAgentBridge)                                       │
│  • Routes tasks to Main Dispatcher                                          │
│  • Tracks conversation for Personality Enhancer                             │
│  • Logs analytics                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MAIN DISPATCHER AGENT                                   │
│                    (LangGraph ReAct Agent)                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Model: gemini-3-flash-preview                                        │  │
│  │  Temperature: 0.3                                                     │  │
│  │  Framework: LangChain + LangGraph                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Dispatch Tools:                                                            │
│  • delegate_to_doc_agent(task)                                              │
│  • delegate_to_todo_agent(task)                                             │
│  • delegate_to_email_agent(task)                                            │
│  • delegate_to_calendar_agent(task)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│    DOC AGENT      │   │   TODO AGENT      │   │   EMAIL AGENT     │
│ (LangGraph ReAct) │   │ (LangGraph ReAct) │   │ (LangGraph ReAct) │
├───────────────────┤   ├───────────────────┤   ├───────────────────┤
│ Model: gemini-3-  │   │ Model: gemini-3-  │   │ Model: gemini-3-  │
│   flash-preview   │   │   flash-preview   │   │   flash-preview   │
│ Temp: 0.5         │   │ Temp: 0.3         │   │ Temp: 0.5         │
├───────────────────┤   ├───────────────────┤   ├───────────────────┤
│ Tools:            │   │ Tools:            │   │ Tools:            │
│ • create_notion   │   │ • add_todo        │   │ • send_email      │
│   _page           │   │ • get_todos       │   │ • draft_email     │
│ • read_notion     │   │ • update_todo     │   │ • check_email     │
│   _page           │   │ • search_notion   │   │   _status         │
│ • search_notion   │   │                   │   │                   │
└───────────────────┘   └───────────────────┘   └───────────────────┘

┌───────────────────┐   ┌─────────────────────────────────────────────┐
│  CALENDAR AGENT   │   │        PERSONALITY ENHANCER AGENT           │
│ (LangGraph ReAct) │   │           (LangGraph ReAct)                 │
├───────────────────┤   ├─────────────────────────────────────────────┤
│ Model: gemini-3-  │   │ Model: gemini-3-flash-preview               │
│   flash-preview   │   │ Temp: 0.6                                   │
│ Temp: 0.3         │   ├─────────────────────────────────────────────┤
├───────────────────┤   │ Tools:                                      │
│ Tools:            │   │ Memory: store, retrieve, search, delete     │
│ • add_calendar    │   │ Analytics: log_metric, log_question_count,  │
│   _event          │   │   log_parameter_change, modify_agent_param  │
│ • get_calendar    │   │   get_current_parameters,                   │
│   _events         │   │   record_conversation_analytics             │
│ • update_calendar │   │                                             │
│   _event          │   │ Responsibilities:                           │
│ • delete_calendar │   │ • Extract & store personal context          │
│   _event          │   │ • Track conversation analytics              │
│ • search_notion   │   │ • Optimize agent parameters                 │
└───────────────────┘   └─────────────────────────────────────────────┘
            │                       │
            ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                  │
├─────────────────────┬──────────────────────┬────────────────────────────────┤
│       NOTION        │       RESEND         │          REDIS                 │
│    (Documents,      │      (Email)         │        (Memory)                │
│   Todos, Calendar)  │                      │                                │
└─────────────────────┴──────────────────────┴────────────────────────────────┘
```

---

## Layer Details

### 1. Voice Agent Layer (Pipecat + Gemini Live + Parallel Deepgram STT)

**File:** `backend/bot.py`

The voice layer uses **Pipecat** framework with **Gemini Live** for native speech-to-speech processing, plus a **ParallelPipeline** with **Deepgram STT** for conversation transcription.

| Component | Description |
|-----------|-------------|
| **GeminiLiveLLMService** | Native audio processing (STT + LLM + TTS in one) |
| **DeepgramSTTService** | Parallel STT for capturing conversation transcripts |
| **ParallelPipeline** | Runs Gemini Live and Deepgram STT branches simultaneously |
| **TranscriptCaptureProcessor** | Captures transcriptions and stores in ConversationStore |
| **Voice** | Puck (configurable: Charon, Kore, Fenrir, Aoede) |
| **Transport** | Daily.co WebRTC or direct WebRTC |
| **Function** | `delegate_task(task_description, task_type)` |

```
┌─────────────────────────────────────────────────────────────────┐
│                    PARALLEL PIPELINE                             │
│   ┌─────────────────────────┬─────────────────────────────┐     │
│   │  Branch 1: Main Flow    │  Branch 2: STT Capture      │     │
│   │  ─────────────────────  │  ─────────────────────────  │     │
│   │  RTVI                   │  DeepgramSTTService         │     │
│   │  GeminiLiveLLMService   │  TranscriptCaptureProcessor │     │
│   └─────────────────────────┴─────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Task Types:**
- `todo` - Add, get, update, complete todos
- `calendar` - Add, get, update, delete events
- `document` - Create, read, search documents
- `email` - Send, draft emails
- `memory` - Remember or recall information
- `general` - Other tasks

---

### 2. Main Dispatcher Agent

**File:** `backend/agents/main_agent.py`

**Class:** `MainDispatcherAgent`

The central orchestrator that routes tasks to specialized sub-agents.

| Property | Value |
|----------|-------|
| **Model** | `gemini-3-flash-preview` |
| **Temperature** | 0.3 (deterministic routing) |
| **Framework** | LangChain + LangGraph (ReAct pattern) |

**Dispatch Tools:**
```python
delegate_to_doc_agent(task: str) -> str
delegate_to_todo_agent(task: str) -> str
delegate_to_email_agent(task: str) -> str
delegate_to_calendar_agent(task: str) -> str
```

**Conversation Context Tools:**
```python
get_conversation_context(mode: str, last_n: int) -> str
# mode: "full", "recent", "user_only", "summary"

search_conversation(query: str) -> str
# Search for specific content in the conversation
```

These tools provide access to the full conversation transcript captured by the parallel Deepgram STT service.

**Routing Logic:**
- Document requests → DocAgent
- Todo/task requests → TodoAgent
- Email requests → EmailAgent
- Calendar/schedule requests → CalendarAgent

---

### 3. Sub-Agents

**File:** `backend/agents/sub_agents.py`

All sub-agents use the same architecture pattern:
- LangChain `ChatGoogleGenerativeAI` for LLM
- LangGraph `create_react_agent` for agent execution
- Custom tools for specific operations

#### DocAgent
| Property | Value |
|----------|-------|
| **Model** | `gemini-3-flash-preview` |
| **Temperature** | 0.5 |
| **Backend** | Notion API |

**Tools:**
- `create_notion_page` - Create new documents
- `read_notion_page` - Read existing documents
- `search_notion` - Search for documents

#### TodoAgent
| Property | Value |
|----------|-------|
| **Model** | `gemini-3-flash-preview` |
| **Temperature** | 0.3 |
| **Backend** | Notion Database |

**Tools:**
- `add_todo` - Add new todo items
- `get_todos` - Retrieve/list todos
- `update_todo` - Edit existing todos
- `search_notion` - Search for todos by name

#### EmailAgent
| Property | Value |
|----------|-------|
| **Model** | `gemini-3-flash-preview` |
| **Temperature** | 0.5 |
| **Backend** | Resend API |

**Tools:**
- `send_email` - Send emails
- `draft_email` - Draft emails for review
- `check_email_status` - Check email status

#### CalendarAgent
| Property | Value |
|----------|-------|
| **Model** | `gemini-3-flash-preview` |
| **Temperature** | 0.3 |
| **Backend** | Notion Database |

**Tools:**
- `add_calendar_event` - Add new events
- `get_calendar_events` - List upcoming events
- `update_calendar_event` - Modify events
- `delete_calendar_event` - Remove events
- `search_notion` - Search for events

---

### 4. Personality Enhancer Agent

**File:** `backend/agents/personality_enhancer.py`

**Class:** `PersonalityEnhancerAgent`

A background agent that improves personalization over time.

| Property | Value |
|----------|-------|
| **Model** | `gemini-3-flash-preview` |
| **Temperature** | 0.6 |
| **Framework** | LangChain + LangGraph (ReAct pattern) |

**Responsibilities:**
1. **Context Memory Management** - Extract and store user preferences
2. **Conversation Analytics** - Track questions asked, topics discussed
3. **Parameter Optimization** - Suggest/apply changes to agent parameters
4. **Voice Preference Detection** - Detect and apply voice speed preferences from conversation

**Tools:**
- Memory: `store_memory`, `retrieve_memory`, `search_memory`, `delete_memory`, `get_conversation_history`
- Analytics: `log_metric`, `log_question_count`, `log_parameter_change`, `modify_agent_parameter`, `get_current_parameters`, `record_conversation_analytics`
- Voice Control: `change_voice_speed`, `change_voice_style`, `get_available_voices`, `get_current_voice_settings`, `add_speaking_instruction`

---

## Data Flow

### Task Execution Flow

```
1. User speaks → "Add a todo to buy groceries"

2. Gemini Live (Voice Agent)
   ├── Processes speech
   ├── Recognizes task intent
   └── Calls: delegate_task(
         task_description="Add a todo: buy groceries",
         task_type="todo"
       )

3. VoiceAgentBridge
   ├── Logs analytics
   ├── Records conversation
   └── Forwards to Main Dispatcher

4. MainDispatcherAgent
   ├── Analyzes task
   └── Calls: delegate_to_todo_agent("Add a todo: buy groceries")

5. TodoAgent
   ├── Uses add_todo tool
   └── Creates todo in Notion

6. Response bubbles back:
   TodoAgent → MainDispatcher → VoiceAgentBridge → Gemini Live → User
   "I've added 'buy groceries' to your todo list"
```

### Analytics Flow

```
1. Conversation starts → PersonalityEnhancer.start_conversation()

2. During conversation:
   ├── Questions tracked → record_question()
   ├── Tasks tracked → record_task_delegation()
   └── Topics tracked → record_topic()

3. Conversation ends → end_conversation()
   ├── Calculate duration
   ├── Log to WandB
   ├── Store summary in Redis
   └── Analyze for personal context
```

---

## Configuration

### Parameters File

**File:** `backend/parameters.py`

All agent configurations are centralized for easy modification:

```python
VOICE_AGENT_CONFIG = {
    "name": "Casey",
    "voice_id": "Puck",
    "temperature": 0.7,
}

MAIN_AGENT_CONFIG = {
    "model": "gemini-3-flash-preview",
    "temperature": 0.3,
}

# Sub-agent configs follow same pattern...
```

### Environment Variables

Required in `.env`:
```
GOOGLE_API_KEY=         # Gemini API
DEEPGRAM_API_KEY=       # Parallel STT for conversation transcription (optional but recommended)
NOTION_API_KEY=         # Notion integration
NOTION_DATABASE_ID=     # Notion todos database
NOTION_CALENDAR_ID=     # Notion calendar database
RESEND_API_KEY=         # Email service
REDIS_URL=              # Memory storage
WANDB_API_KEY=          # Analytics tracking
DAILY_API_KEY=          # WebRTC transport
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Google Gemini 3 Flash Preview |
| **Voice** | Pipecat + Gemini Live (native audio) |
| **Agent Framework** | LangChain + LangGraph |
| **Agent Pattern** | ReAct (Reasoning + Acting) |
| **Documents/Todos/Calendar** | Notion API |
| **Email** | Resend API |
| **Memory** | Redis |
| **Analytics** | Weights & Biases (WandB) |
| **Transport** | Daily.co WebRTC |
| **Frontend** | React + TypeScript + Electron |

"""
Pipecat voice bot for zero_me using Gemini Live (native audio)
Compatible with Pipecat Cloud deployment and local development

Uses Gemini's built-in speech-to-speech capabilities with function calling.
The voice agent has tools for:
1. delegate_task - routes to sub-agents for complex tasks
2. remember_info - quick memory storage
3. recall_info - quick memory retrieval
"""
import os
import asyncio

from dotenv import load_dotenv
from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.google.gemini_live import GeminiLiveLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams

# Load environment variables
load_dotenv(override=True)

# Import parameters from centralized config
from parameters import VOICE_AGENT_SYSTEM_PROMPT, VOICE_AGENT_CONFIG

# Import agent system
from agents.main_agent import get_main_agent
from agents.personality_enhancer import get_personality_enhancer
from analytics import get_analytics_manager
from memory import get_memory_manager

# Default user ID
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "default_user")


class VoiceAgentBridge:
    """
    Bridge between the Pipecat voice pipeline and the LangChain agent system.
    
    This class handles:
    1. Task delegation from voice agent to main dispatcher
    2. Direct memory operations (remember/recall)
    3. Conversation tracking for the personality enhancer
    4. Analytics logging
    5. Session end processing (memory updates, WandB logging, parameter updates)
    """
    
    def __init__(self):
        self.main_agent = None  # Lazy initialization
        self.personality_enhancer = None  # Lazy initialization
        self.analytics = None
        self.memory = None
        self._initialized = False
        self.conversation_text = []  # Store conversation for analysis
        self.conversation_id = None
        self.user_id = DEFAULT_USER_ID
    
    def initialize(self):
        """Initialize the agent system (called when first client connects)."""
        if self._initialized:
            return
        
        try:
            logger.info("🚀 Initializing agent system...")
            self.main_agent = get_main_agent()
            self.personality_enhancer = get_personality_enhancer()
            self.analytics = get_analytics_manager()
            self.memory = get_memory_manager()
            self._initialized = True
            logger.info("✅ Agent system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent system: {e}")
            # Continue without agent system - voice will still work
            self._initialized = False
    
    def start_conversation(self):
        """Start tracking a new conversation."""
        import uuid
        self.conversation_id = str(uuid.uuid4())[:8]
        
        if self.personality_enhancer:
            self.personality_enhancer.start_conversation()
        self.conversation_text = []
        logger.info(f"📞 New conversation started: {self.conversation_id}")
    
    def record_user_message(self, text: str):
        """Record a user message for analysis."""
        self.conversation_text.append(f"User: {text}")
        logger.debug(f"👤 User: {text}")
    
    def record_assistant_message(self, text: str):
        """Record an assistant message for analysis."""
        self.conversation_text.append(f"Assistant: {text}")
        logger.debug(f"🤖 Assistant: {text}")
        
        # Check if assistant asked a question
        if "?" in text and self.personality_enhancer:
            self.personality_enhancer.record_question()
    
    async def remember_info(self, key: str, value: str) -> dict:
        """
        Store information in memory directly.
        
        Args:
            key: What to remember (e.g., "favorite_color", "birthday")
            value: The value to remember
        
        Returns:
            Result dict
        """
        if not self.memory:
            self.initialize()
        
        if not self.memory or not self.memory.is_available():
            return {"success": False, "result": "Memory is not available right now."}
        
        try:
            logger.info(f"💾 REMEMBER: {key} = {value}")
            
            success = self.memory.store_context(self.user_id, key, value, category="user_info")
            
            if self.analytics:
                self.analytics.log_memory_operation("store", self.user_id, key, success)
            
            if success:
                return {"success": True, "result": f"I'll remember that: {key} is {value}"}
            else:
                return {"success": False, "result": "Failed to store in memory."}
                
        except Exception as e:
            logger.error(f"❌ Memory store error: {e}")
            return {"success": False, "result": f"Error: {str(e)}"}
    
    async def recall_info(self, key: str = None, search_query: str = None) -> dict:
        """
        Recall information from memory.
        
        Args:
            key: Specific key to recall (optional)
            search_query: Search term to find relevant memories (optional)
        
        Returns:
            Result dict with recalled information
        """
        if not self.memory:
            self.initialize()
        
        if not self.memory or not self.memory.is_available():
            return {"success": False, "result": "Memory is not available right now."}
        
        try:
            if key:
                logger.info(f"🔍 RECALL: {key}")
                result = self.memory.retrieve_context(self.user_id, key)
                
                if result:
                    return {"success": True, "result": f"{key}: {result.get('value', 'Unknown')}"}
                else:
                    return {"success": True, "result": f"I don't remember anything about '{key}'."}
            
            elif search_query:
                logger.info(f"🔍 SEARCH MEMORY: {search_query}")
                results = self.memory.search_context(self.user_id, search_query)
                
                if results:
                    memories = [f"- {r.get('key')}: {r.get('value')}" for r in results]
                    return {"success": True, "result": f"Found {len(results)} related memories:\n" + "\n".join(memories)}
                else:
                    return {"success": True, "result": f"No memories found related to '{search_query}'."}
            
            else:
                # Get all memories
                logger.info(f"🔍 RECALL ALL MEMORIES")
                result = self.memory.retrieve_context(self.user_id, None)
                
                if result:
                    memories = [f"- {k}: {v.get('value', 'Unknown')}" for k, v in result.items()]
                    return {"success": True, "result": "Here's what I remember:\n" + "\n".join(memories[:10])}
                else:
                    return {"success": True, "result": "I don't have any memories stored yet."}
                
        except Exception as e:
            logger.error(f"❌ Memory recall error: {e}")
            return {"success": False, "result": f"Error: {str(e)}"}
    
    async def delegate_task(self, task_description: str, task_type: str = "general") -> dict:
        """
        Delegate a task to the main dispatcher agent.
        
        Args:
            task_description: The task description from the voice agent
            task_type: Category of the task (todo, calendar, document, email, memory, general)
        
        Returns:
            Result dict from the sub-agent
        """
        if not self.main_agent:
            self.initialize()
        
        if not self.main_agent:
            return {"success": False, "result": "The task system is not available right now. Please try again later."}
        
        try:
            logger.info(f"🔧 DELEGATE_TASK called: type='{task_type}', task='{task_description[:80]}...'")
            
            # Record task delegation
            if self.personality_enhancer:
                self.personality_enhancer.record_task_delegation()
                self.personality_enhancer.record_topic(task_type)
            
            # Execute via main agent
            result = await self.main_agent.dispatch(task_description)
            
            logger.info(f"✅ Task completed: {result[:100]}...")
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.error(f"❌ Task delegation error: {e}")
            return {"success": False, "result": f"I encountered an issue: {str(e)}"}
    
    async def end_conversation(self):
        """
        End the conversation and trigger all end-of-session processing:
        1. Store conversation summary in memory
        2. Update personality/parameters based on conversation
        3. Log analytics to WandB
        4. Prepare for next session
        """
        if not self._initialized:
            logger.info("Conversation ended: No active session.")
            return
        
        logger.info("=" * 60)
        logger.info("🏁 SESSION ENDING - Processing conversation...")
        logger.info("=" * 60)
        
        try:
            # 1. Get conversation summary from personality enhancer
            summary = None
            if self.personality_enhancer:
                summary = await self.personality_enhancer.end_conversation(self.user_id)
                logger.info(f"📊 Conversation summary:\n{summary}")
            
            # 2. Analyze conversation and store context in memory
            if self.conversation_text and self.personality_enhancer:
                full_text = "\n".join(self.conversation_text)
                logger.info(f"📝 Analyzing {len(self.conversation_text)} conversation turns...")
                
                # This will:
                # - Extract personal information
                # - Store relevant context to memory
                # - Update parameters if needed
                # - Log to WandB
                await self.personality_enhancer.analyze_and_store_context(
                    full_text, self.user_id
                )
            
            # 3. Log session metrics to WandB (personality enhancer already logs detailed metrics)
            if self.analytics:
                self.analytics.log_conversation_end(
                    conversation_id=self.conversation_id,
                    user_id=self.user_id,
                    questions_asked=self.personality_enhancer.current_conversation.get("questions_asked", 0) if self.personality_enhancer else 0,
                    tasks_delegated=self.personality_enhancer.current_conversation.get("tasks_delegated", 0) if self.personality_enhancer else 0,
                    topics=self.personality_enhancer.topics if self.personality_enhancer else [],
                    summary=summary
                )
                logger.info("📈 Session metrics logged to WandB")
            
            # 4. Store conversation in memory for future reference
            if self.memory and self.memory.is_available() and summary:
                # store_conversation_summary is sync, expects summary as dict
                self.memory.store_conversation_summary(
                    user_id=self.user_id,
                    summary={"text": summary} if isinstance(summary, str) else summary,
                    topics=self.personality_enhancer.topics if self.personality_enhancer else [],
                    duration=0  # We don't track duration yet
                )
                logger.info("💾 Conversation summary stored in memory")
            
            logger.info("✅ Session processing complete - Ready for next conversation")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Error during session end processing: {e}")
            import traceback
            logger.error(traceback.format_exc())


# Global bridge instance
voice_bridge = VoiceAgentBridge()


# ============================================
# FUNCTION DEFINITIONS FOR GEMINI LIVE
# ============================================

# Tool 1: Delegate task to sub-agents
delegate_task_schema = FunctionSchema(
    name="delegate_task",
    description="""Execute a task by delegating to the appropriate agent. 
Use this for ANY action the user wants to perform:
- Todo tasks: add, get, update, complete todos
- Calendar: add, get, update, delete events  
- Documents: create, read, search documents
- Email: send, draft emails

ALWAYS use this tool when the user asks you to DO something actionable.
For example: "add a todo", "schedule a meeting", "send an email", "create a note".""",
    properties={
        "task_description": {
            "type": "string",
            "description": "A clear description of what the user wants to accomplish. Include all relevant details like names, dates, times, email addresses, content, etc."
        },
        "task_type": {
            "type": "string",
            "enum": ["todo", "calendar", "document", "email", "general"],
            "description": "The category of task: todo (tasks/todos), calendar (events/schedule), document (notes/docs), email (send/draft), general (other)"
        }
    },
    required=["task_description", "task_type"]
)

# Tool 2: Remember information (quick memory storage)
remember_info_schema = FunctionSchema(
    name="remember_info",
    description="""Store personal information in memory for future reference.
Use this when the user tells you something about themselves that you should remember.

Examples:
- "My favorite color is blue" → remember_info(key="favorite_color", value="blue")
- "I work at Google" → remember_info(key="workplace", value="Google")
- "Call me Alex" → remember_info(key="preferred_name", value="Alex")
- "My birthday is March 15" → remember_info(key="birthday", value="March 15")""",
    properties={
        "key": {
            "type": "string",
            "description": "A descriptive key for what to remember (e.g., 'favorite_color', 'birthday', 'workplace', 'preferred_name')"
        },
        "value": {
            "type": "string",
            "description": "The value to remember"
        }
    },
    required=["key", "value"]
)

# Tool 3: Recall information (quick memory retrieval)
recall_info_schema = FunctionSchema(
    name="recall_info",
    description="""Retrieve personal information from memory.
Use this when the user asks about something you should remember, or when you need context about the user.

Examples:
- "What's my favorite color?" → recall_info(key="favorite_color")
- "What do you know about me?" → recall_info() (no key = get all memories)
- "Do you remember anything about my work?" → recall_info(search_query="work")""",
    properties={
        "key": {
            "type": "string",
            "description": "Specific key to recall (optional). Leave empty to get all memories."
        },
        "search_query": {
            "type": "string",
            "description": "Search term to find relevant memories (optional). Use this for fuzzy searches."
        }
    },
    required=[]
)

# Create tools schema with all three tools
tools = ToolsSchema(standard_tools=[
    delegate_task_schema,
    remember_info_schema,
    recall_info_schema
])


# Build the system prompt with all tool capabilities
ENHANCED_SYSTEM_PROMPT = VOICE_AGENT_SYSTEM_PROMPT + """

# Your Tools - USE THEM!

You have THREE tools available. Use them proactively:

## 1. delegate_task
For actionable tasks: todos, calendar events, documents, emails.
- "Add a todo to buy groceries" → delegate_task(task_description="Add todo: buy groceries", task_type="todo")
- "Send an email to john@example.com" → delegate_task(task_description="Send email to john@example.com", task_type="email")

## 2. remember_info
When the user tells you personal info, ALWAYS remember it:
- "My favorite color is blue" → remember_info(key="favorite_color", value="blue")
- "I'm working on a startup" → remember_info(key="current_project", value="working on a startup")
- "Call me Tarun" → remember_info(key="preferred_name", value="Tarun")

## 3. recall_info
When the user asks what you know or references past info:
- "What's my favorite color?" → recall_info(key="favorite_color")
- "What do you know about me?" → recall_info()
- "What did I tell you about work?" → recall_info(search_query="work")

IMPORTANT:
- When someone tells you something personal, USE remember_info immediately
- When someone asks what you remember, USE recall_info
- DO NOT just say "I'll remember that" - actually call remember_info!
"""


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Main bot logic - runs the voice assistant pipeline"""
    logger.info("Starting bot")

    # Check for required API key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.error("GOOGLE_API_KEY not found in environment")
        raise ValueError("GOOGLE_API_KEY is required")

    # Initialize the voice-agent bridge
    voice_bridge.initialize()

    # Gemini Live - Native speech-to-speech LLM with function calling
    llm = GeminiLiveLLMService(
        api_key=google_api_key,
        system_instruction=ENHANCED_SYSTEM_PROMPT,
        voice_id=VOICE_AGENT_CONFIG.get("voice_id", "Puck"),
        tools=tools,  # Pass the tools schema for function calling
    )
    
    logger.info("🔧 Tools configured:")
    logger.info("   1. delegate_task → routes to Todo, Calendar, Doc, Email agents")
    logger.info("   2. remember_info → stores info in Redis memory")
    logger.info("   3. recall_info → retrieves info from Redis memory")
    
    # ===== FUNCTION HANDLERS =====
    
    async def handle_delegate_task(params: FunctionCallParams):
        """Handle the delegate_task function call from Gemini."""
        task_description = params.arguments.get("task_description", "")
        task_type = params.arguments.get("task_type", "general")
        
        # Yellow color for tool calls
        YELLOW = "\033[1;33m"
        CYAN = "\033[1;36m"
        RESET = "\033[0m"
        
        print(f"\n{YELLOW}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{YELLOW}║  🎯 FUNCTION CALL: delegate_task{RESET}")
        print(f"{YELLOW}║  📋 Type: {task_type}{RESET}")
        print(f"{YELLOW}║  📝 Task: {task_description[:60]}...{RESET}")
        print(f"{YELLOW}╚══════════════════════════════════════════════════════════╝{RESET}")
        
        result = await voice_bridge.delegate_task(task_description, task_type)
        await params.result_callback(result)
        
        print(f"{CYAN}║  📤 Result: {result.get('result', '')[:60]}...{RESET}")
    
    async def handle_remember_info(params: FunctionCallParams):
        """Handle the remember_info function call from Gemini."""
        key = params.arguments.get("key", "")
        value = params.arguments.get("value", "")
        
        # Magenta/Purple for memory operations
        MAGENTA = "\033[1;35m"
        CYAN = "\033[1;36m"
        RESET = "\033[0m"
        
        print(f"\n{MAGENTA}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{MAGENTA}║  💾 FUNCTION CALL: remember_info{RESET}")
        print(f"{MAGENTA}║  🔑 Key: {key}{RESET}")
        print(f"{MAGENTA}║  📝 Value: {value[:60]}...{RESET}")
        print(f"{MAGENTA}╚══════════════════════════════════════════════════════════╝{RESET}")
        
        result = await voice_bridge.remember_info(key, value)
        await params.result_callback(result)
        
        print(f"{CYAN}║  📤 Result: {result.get('result', '')[:60]}...{RESET}")
    
    async def handle_recall_info(params: FunctionCallParams):
        """Handle the recall_info function call from Gemini."""
        key = params.arguments.get("key")
        search_query = params.arguments.get("search_query")
        
        # Blue for recall/search operations
        BLUE = "\033[1;34m"
        CYAN = "\033[1;36m"
        RESET = "\033[0m"
        
        print(f"\n{BLUE}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BLUE}║  🔍 FUNCTION CALL: recall_info{RESET}")
        print(f"{BLUE}║  🔑 Key: {key}{RESET}")
        print(f"{BLUE}║  🔎 Search: {search_query}{RESET}")
        print(f"{BLUE}╚══════════════════════════════════════════════════════════╝{RESET}")
        
        result = await voice_bridge.recall_info(key, search_query)
        await params.result_callback(result)
        
        print(f"{CYAN}║  📤 Result: {result.get('result', '')[:60]}...{RESET}")
    
    # Register all function handlers
    llm.register_function("delegate_task", handle_delegate_task, cancel_on_interruption=False)
    llm.register_function("remember_info", handle_remember_info, cancel_on_interruption=False)
    llm.register_function("recall_info", handle_recall_info, cancel_on_interruption=False)
    
    logger.info("✅ All functions registered")

    # RTVI processor for frontend state communication
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Pipeline: audio in -> RTVI -> Gemini Live (STT+LLM+TTS with tools) -> audio out
    pipeline = Pipeline([
        transport.input(),
        rtvi,
        llm,
        transport.output(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")
        voice_bridge.start_conversation()

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        # End conversation and process all analytics/memory/wandb
        asyncio.create_task(voice_bridge.end_conversation())
        await task.cancel()

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info(f"Participant joined: {participant.get('id', 'unknown')}")

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info(f"Participant left: {participant.get('id', 'unknown')}, reason: {reason}")
        # End conversation and process all analytics/memory/wandb
        asyncio.create_task(voice_bridge.end_conversation())
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    logger.info("🎙️ Bot running with Gemini Live + Function Calling")
    logger.info("📋 Tools: delegate_task, remember_info, recall_info")
    await runner.run(task)
    logger.info("Bot finished")


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat runner."""
    logger.info(f"Running in {'local' if os.environ.get('ENV') == 'local' else 'cloud'} mode")

    # Transport params following Pipecat's expected pattern
    # Use DailyParams for daily transport, TransportParams for webrtc
    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }

    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()

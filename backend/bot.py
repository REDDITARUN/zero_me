"""
Pipecat voice bot for zero_me using Gemini Live (native audio)
Compatible with Pipecat Cloud deployment and local development

Uses Gemini's built-in speech-to-speech capabilities with function calling.
The voice agent has ONE tool (delegate_task) that routes to the agent system.
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


class VoiceAgentBridge:
    """
    Bridge between the Pipecat voice pipeline and the LangChain agent system.
    
    This class handles:
    1. Task delegation from voice agent to main dispatcher
    2. Conversation tracking for the personality enhancer
    3. Analytics logging
    """
    
    def __init__(self):
        self.main_agent = None  # Lazy initialization
        self.personality_enhancer = None  # Lazy initialization
        self.analytics = None
        self._initialized = False
        self.conversation_text = []  # Store conversation for analysis
    
    def initialize(self):
        """Initialize the agent system (called when first client connects)."""
        if self._initialized:
            return
        
        try:
            logger.info("🚀 Initializing agent system...")
            self.main_agent = get_main_agent()
            self.personality_enhancer = get_personality_enhancer()
            self.analytics = get_analytics_manager()
            self._initialized = True
            logger.info("✅ Agent system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent system: {e}")
            # Continue without agent system - voice will still work
            self._initialized = False
    
    def start_conversation(self):
        """Start tracking a new conversation."""
        if self.personality_enhancer:
            self.personality_enhancer.start_conversation()
        self.conversation_text = []
        logger.info("📞 New conversation started")
    
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
    
    async def end_conversation(self, user_id: str = "default_user"):
        """End the conversation and process analytics."""
        if not self.personality_enhancer:
            logger.info("Conversation ended: No active conversation to end.")
            return
        
        try:
            # End conversation tracking
            summary = await self.personality_enhancer.end_conversation(user_id)
            logger.info(f"Conversation ended: {summary}")
            
            # Analyze conversation for personal context
            if self.conversation_text:
                full_text = "\n".join(self.conversation_text)
                await self.personality_enhancer.analyze_and_store_context(
                    full_text, user_id
                )
            
        except Exception as e:
            logger.error(f"Error ending conversation: {e}")


# Global bridge instance
voice_bridge = VoiceAgentBridge()


# ============================================
# FUNCTION DEFINITION FOR GEMINI LIVE
# ============================================

# Define the ONE universal tool that routes to the agent system
delegate_task_schema = FunctionSchema(
    name="delegate_task",
    description="""Execute a task by delegating to the appropriate agent. 
Use this for ANY action the user wants to perform:
- Todo tasks: add, get, update, complete todos
- Calendar: add, get, update, delete events  
- Documents: create, read, search documents
- Email: send, draft emails
- Memory: remember or recall information about the user

ALWAYS use this tool when the user asks you to DO something, not just chat.
For example: "add a todo", "schedule a meeting", "send an email", "remember that I like coffee".""",
    properties={
        "task_description": {
            "type": "string",
            "description": "A clear description of what the user wants to accomplish. Include all relevant details like names, dates, times, email addresses, content, etc."
        },
        "task_type": {
            "type": "string",
            "enum": ["todo", "calendar", "document", "email", "memory", "general"],
            "description": "The category of task: todo (tasks/todos), calendar (events/schedule), document (notes/docs), email (send/draft), memory (remember info), general (other)"
        }
    },
    required=["task_description", "task_type"]
)

# Create tools schema
tools = ToolsSchema(standard_tools=[delegate_task_schema])


# Build the system prompt with task delegation capability
ENHANCED_SYSTEM_PROMPT = VOICE_AGENT_SYSTEM_PROMPT + """

# Task Delegation - CRITICAL

You have access to a tool called `delegate_task`. You MUST use it whenever the user asks you to:
- Add, check, or update todos/tasks
- Add, check, or modify calendar events
- Create or read documents/notes
- Send or draft emails
- Remember something about them

When you need to use the tool:
1. Tell the user you're working on it (e.g., "Let me add that for you...")
2. Call the delegate_task function with a clear task_description and appropriate task_type
3. Wait for the result
4. Report the result back to the user naturally

Examples of when to use delegate_task:
- "Add a todo to buy groceries" → delegate_task(task_description="Add a todo: buy groceries", task_type="todo")
- "What's on my calendar?" → delegate_task(task_description="Get all calendar events", task_type="calendar")
- "Remember my favorite color is blue" → delegate_task(task_description="Store: user's favorite color is blue", task_type="memory")
- "Send an email to john@example.com about the meeting" → delegate_task(task_description="Send email to john@example.com about the meeting", task_type="email")

DO NOT just say you'll do something - actually call the delegate_task function!
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
    
    logger.info(f"🔧 Tools configured: delegate_task (routes to sub-agents)")
    
    # Register the delegate_task function handler
    async def handle_delegate_task(params: FunctionCallParams):
        """Handle the delegate_task function call from Gemini."""
        task_description = params.arguments.get("task_description", "")
        task_type = params.arguments.get("task_type", "general")
        
        logger.info(f"")
        logger.info(f"🎯 ═══════════════════════════════════════════════════════")
        logger.info(f"🎯 FUNCTION CALL RECEIVED: delegate_task")
        logger.info(f"🎯 Task Type: {task_type}")
        logger.info(f"🎯 Task: {task_description}")
        logger.info(f"🎯 ═══════════════════════════════════════════════════════")
        
        # Execute the task via the bridge
        result = await voice_bridge.delegate_task(task_description, task_type)
        
        # Return the result to Gemini
        await params.result_callback(result)
        logger.info(f"📤 Function result sent: {result.get('result', '')[:80]}...")
    
    # Register the function with the LLM
    llm.register_function(
        "delegate_task",
        handle_delegate_task,
        cancel_on_interruption=False  # Don't cancel if user interrupts - let the task complete
    )
    
    logger.info("✅ Registered function: delegate_task")

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
        # End conversation and process analytics
        asyncio.create_task(voice_bridge.end_conversation())
        await task.cancel()

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info(f"Participant joined: {participant.get('id', 'unknown')}")

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info(f"Participant left: {participant.get('id', 'unknown')}, reason: {reason}")
        # End conversation and process analytics
        asyncio.create_task(voice_bridge.end_conversation())
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    logger.info("🎙️ Bot running with Gemini Live + Function Calling")
    logger.info("📋 Tool available: delegate_task → routes to Todo, Calendar, Doc, Email, Memory agents")
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

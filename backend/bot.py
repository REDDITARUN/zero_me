"""
Pipecat voice bot for zero_me using Gemini Live (native audio)
Compatible with Pipecat Cloud deployment and local development

Uses Gemini's built-in speech-to-speech capabilities with LangChain agent integration.
The voice agent can delegate tasks to the main dispatcher agent which routes to sub-agents.
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
            logger.info("Initializing agent system...")
            self.main_agent = get_main_agent()
            self.personality_enhancer = get_personality_enhancer()
            self.analytics = get_analytics_manager()
            self._initialized = True
            logger.info("Agent system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent system: {e}")
            # Continue without agent system - voice will still work
            self._initialized = False
    
    def start_conversation(self):
        """Start tracking a new conversation."""
        if self.personality_enhancer:
            self.personality_enhancer.start_conversation()
        self.conversation_text = []
    
    def record_user_message(self, text: str):
        """Record a user message for analysis."""
        self.conversation_text.append(f"User: {text}")
    
    def record_assistant_message(self, text: str):
        """Record an assistant message for analysis."""
        self.conversation_text.append(f"Assistant: {text}")
        
        # Check if assistant asked a question
        if "?" in text and self.personality_enhancer:
            self.personality_enhancer.record_question()
    
    async def delegate_task(self, task: str) -> str:
        """
        Delegate a task to the main dispatcher agent.
        
        Args:
            task: The task description from the voice agent
        
        Returns:
            Result from the sub-agent
        """
        if not self.main_agent:
            self.initialize()
        
        if not self.main_agent:
            return "I'm sorry, the task system is not available right now."
        
        try:
            logger.info(f"Delegating task: {task[:100]}...")
            
            # Record task delegation
            if self.personality_enhancer:
                self.personality_enhancer.record_task_delegation()
            
            # Execute via main agent
            result = await self.main_agent.dispatch(task)
            
            return result
            
        except Exception as e:
            logger.error(f"Task delegation error: {e}")
            return f"I encountered an issue: {str(e)}"
    
    async def end_conversation(self, user_id: str = "default_user"):
        """End the conversation and process analytics."""
        if not self.personality_enhancer:
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


# Build the system prompt with task delegation capability
ENHANCED_SYSTEM_PROMPT = VOICE_AGENT_SYSTEM_PROMPT + """

# Task Delegation

When the user asks you to do something concrete like:
- Create a document, note, or page
- Add a todo or task
- Send an email
- Add, modify, or check calendar events

Acknowledge the request and tell them you're handling it. The task system will process it automatically.

Examples:
- User: "Add a todo to buy groceries"
  You: "I'll add that to your todo list... Done! I've added 'buy groceries' to your todos."

- User: "Send an email to john@example.com about the meeting"
  You: "I'll draft that email for you... I've sent an email to John about the meeting."

- User: "What's on my calendar tomorrow?"
  You: "Let me check your calendar... You have a team meeting at 10 AM and a dentist appointment at 3 PM."
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

    # Gemini Live - Native speech-to-speech LLM
    # This handles STT, LLM, and TTS all in one service
    llm = GeminiLiveLLMService(
        api_key=google_api_key,
        system_instruction=ENHANCED_SYSTEM_PROMPT,
        voice_id=VOICE_AGENT_CONFIG.get("voice_id", "Puck"),
    )

    # RTVI processor for frontend state communication
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Pipeline: audio in -> RTVI -> Gemini Live (STT+LLM+TTS) -> audio out
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

    logger.info("Bot running with Gemini Live (native audio) + LangChain agents...")
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

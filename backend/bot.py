"""
Pipecat voice bot for zero_me using Gemini Live (native audio)
Compatible with Pipecat Cloud deployment and local development

Uses Gemini's built-in speech-to-speech capabilities - no separate STT/TTS needed
"""
import os

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

load_dotenv(override=True)

SYSTEM_PROMPT = """You are a friendly, reliable voice assistant that answers questions, explains topics, and helps with tasks.

# Voice Interaction Rules

You are having a voice conversation. Follow these rules:

- Respond in plain conversational text. No markdown, lists, code blocks, or emojis.
- Keep responses brief: 1-3 sentences usually. Be concise.
- Spell out numbers and abbreviations for clarity.
- Ask one question at a time.
- Be warm and helpful but efficient.

# Conversation Style

- Greet users warmly when they first speak
- Listen carefully and respond naturally
- Confirm understanding before taking actions
- Summarize when completing a topic

# Safety

- Stay within safe, lawful, appropriate topics
- For medical/legal/financial topics, provide general info and suggest consulting professionals
- Protect user privacy"""


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Main bot logic - runs the voice assistant pipeline"""
    logger.info("Starting bot")

    # Check for required API key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.error("GOOGLE_API_KEY not found in environment")
        raise ValueError("GOOGLE_API_KEY is required")

    # Gemini Live - Native speech-to-speech LLM
    # This handles STT, LLM, and TTS all in one service
    llm = GeminiLiveLLMService(
        api_key=google_api_key,
        system_instruction=SYSTEM_PROMPT,
        voice_id="Puck",  # Options: Puck, Charon, Kore, Fenrir, Aoede
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

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await task.cancel()

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info(f"Participant joined: {participant.get('id', 'unknown')}")

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info(f"Participant left: {participant.get('id', 'unknown')}, reason: {reason}")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    logger.info("Bot running with Gemini Live (native audio)...")
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

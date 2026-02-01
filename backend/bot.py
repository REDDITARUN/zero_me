"""
Pipecat voice bot for zero_me using Gemini Live (native audio)
Uses Gemini's built-in speech-to-speech capabilities - no separate STT/TTS needed
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.services.google.gemini_live import GeminiLiveLLMService

load_dotenv(".env.local", override=True)

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


async def main():
    """Main bot entry point"""
    # Get room URL from command line args
    room_url = None
    for i, arg in enumerate(sys.argv):
        if arg == "--room-url" and i + 1 < len(sys.argv):
            room_url = sys.argv[i + 1]
            break
    
    if not room_url:
        logger.error("No --room-url provided")
        sys.exit(1)
    
    logger.info(f"Connecting to room: {room_url}")
    
    # Check for required API key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.error("GOOGLE_API_KEY not found in environment")
        sys.exit(1)
    
    # Daily transport for WebRTC audio
    transport = DailyTransport(
        room_url,
        None,  # No token needed for the bot
        "Assistant",
        DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
        ),
    )

    # Gemini Live - Native speech-to-speech LLM
    # This handles STT, LLM, and TTS all in one service
    llm = GeminiLiveLLMService(
        api_key=google_api_key,
        system_instruction=SYSTEM_PROMPT,
        voice_id="Puck",  # Options: Puck, Charon, Kore, Fenrir, Aoede
    )

    # RTVI processor for frontend state communication
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # VAD for voice activity detection
    vad = SileroVADAnalyzer(params=VADParams(stop_secs=0.5))

    # Pipeline: audio in -> VAD -> Gemini Live (STT+LLM+TTS) -> audio out
    pipeline = Pipeline([
        transport.input(),
        vad,
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

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info(f"Participant joined: {participant['id']}")
        # Gemini Live will automatically start listening and respond when user speaks

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info(f"Participant left: {participant['id']}, reason: {reason}")
        await task.cancel()

    runner = PipelineRunner()
    
    logger.info("Bot starting with Gemini Live (native audio)...")
    await runner.run(task)
    logger.info("Bot finished")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

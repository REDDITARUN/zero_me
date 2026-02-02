"""
LOCAL DEVELOPMENT SERVER for Pipecat (self-hosted mode)

This server is ONLY needed for local development when NOT using Pipecat Cloud.
When deploying to Pipecat Cloud, this file is not used - Pipecat Cloud handles
room creation and bot lifecycle automatically.

Use this when:
- Running locally without Pipecat Cloud
- Testing before deploying to Pipecat Cloud
- Need full control over infrastructure

Run with: python server.py
"""
import os
import subprocess
import sys
import threading
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
from dotenv import load_dotenv
from loguru import logger

from tool_status import get_tool_status_broadcaster
from tools.voice_tools import get_voice_manager, VOICE_PROFILES, PACE_TO_VOICES
from pydantic import BaseModel

load_dotenv(".env.local")


# Request models for voice settings
class VoiceChangeRequest(BaseModel):
    voice_id: str
    reason: str = "manual_ui_change"


class PaceChangeRequest(BaseModel):
    pace: str  # "fast", "moderate", "slow"
    reason: str = "manual_ui_change"


class PromptInstructionRequest(BaseModel):
    instruction: str
    category: str = "speaking_style"

app = FastAPI(title="Zero Me - Local Development Server")

# CORS for Electron app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DAILY_API_KEY = os.getenv("DAILY_API_KEY")
DAILY_API_URL = "https://api.daily.co/v1"


def log_bot_output(process, room_name):
    """Log bot stdout/stderr in a separate thread"""
    def stream_output(stream, prefix):
        for line in iter(stream.readline, b''):
            try:
                decoded = line.decode('utf-8').strip()
                if decoded:
                    logger.info(f"[Bot {room_name}] {prefix}: {decoded}")
            except:
                pass
    
    # Stream stdout
    stdout_thread = threading.Thread(target=stream_output, args=(process.stdout, "OUT"))
    stdout_thread.daemon = True
    stdout_thread.start()
    
    # Stream stderr
    stderr_thread = threading.Thread(target=stream_output, args=(process.stderr, "ERR"))
    stderr_thread.daemon = True
    stderr_thread.start()


async def create_daily_room() -> dict:
    """Create a Daily room for the voice session"""
    if not DAILY_API_KEY:
        raise HTTPException(status_code=500, detail="DAILY_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DAILY_API_URL}/rooms",
            headers={"Authorization": f"Bearer {DAILY_API_KEY}"},
            json={
                "properties": {
                    "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
                    "enable_chat": False,
                    "enable_screenshare": False,
                    "enable_knocking": False,
                    "start_video_off": True,
                    "start_audio_off": False,
                }
            },
            timeout=10.0,
        )
        if response.status_code != 200:
            logger.error(f"Failed to create Daily room: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to create room")
        return response.json()


async def create_daily_token(room_name: str, is_owner: bool = False) -> str:
    """Create a Daily meeting token for the user"""
    if not DAILY_API_KEY:
        raise HTTPException(status_code=500, detail="DAILY_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DAILY_API_URL}/meeting-tokens",
            headers={"Authorization": f"Bearer {DAILY_API_KEY}"},
            json={
                "properties": {
                    "room_name": room_name,
                    "is_owner": is_owner,
                    "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
                }
            },
            timeout=10.0,
        )
        if response.status_code != 200:
            logger.error(f"Failed to create Daily token: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to create token")
        return response.json()["token"]


def launch_bot_process(room_url: str, room_name: str):
    """Launch the bot as a subprocess to join the Daily room"""
    bot_script = os.path.join(os.path.dirname(__file__), "bot.py")
    
    # Use the same Python from venv
    python_path = sys.executable
    
    # Prepare environment with all needed vars
    env = os.environ.copy()
    env["ENV"] = "local"
    # Pass Daily room URL via environment variable (required by pipecat runner)
    env["DAILY_ROOM_URL"] = room_url
    
    logger.info(f"Launching bot with Python: {python_path}")
    logger.info(f"Bot script: {bot_script}")
    logger.info(f"Room URL: {room_url}")
    
    # Launch bot using the pipecat runner with daily transport
    # -d flag = direct Daily connection, room URL from DAILY_ROOM_URL env var
    process = subprocess.Popen(
        [
            python_path,
            "-m", "pipecat.runner.run",
            "-t", "daily",
            "-d",  # Direct connection to Daily room
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(__file__),
    )
    
    # Start logging threads
    log_bot_output(process, room_name)
    
    logger.info(f"Launched bot process (PID: {process.pid}) for room: {room_name}")
    return process.pid


@app.post("/connect")
async def connect():
    """
    Connect endpoint - creates a Daily room and launches the bot.
    
    Returns connection details for the frontend to join the same room.
    The bot joins the room as a participant and handles voice interaction.
    
    NOTE: This endpoint mimics the Pipecat Cloud /start endpoint response format
    for compatibility with the frontend.
    """
    logger.info("New connection request (local development mode)")
    
    # Create Daily room
    room = await create_daily_room()
    room_url = room["url"]
    room_name = room["name"]
    logger.info(f"Created Daily room: {room_name}")
    
    # Create token for the user
    user_token = await create_daily_token(room_name, is_owner=False)
    
    # Launch bot to join the room
    bot_pid = launch_bot_process(room_url, room_name)
    
    # Return connection details for the client
    # Format matches Pipecat Cloud response for frontend compatibility
    return JSONResponse({
        "room_url": room_url,
        "token": user_token,
    })


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "zero-me-local", "mode": "development"}


@app.get("/status/stream")
async def status_stream():
    """
    Server-Sent Events endpoint for real-time tool status updates.
    Frontend connects here to receive live architecture flow visualization.
    """
    async def event_generator():
        broadcaster = get_tool_status_broadcaster()
        queue = broadcaster.subscribe()
        
        try:
            # Send initial state
            initial_data = {
                "type": "init",
                "timestamp": datetime.now().timestamp(),
                "data": {
                    "architecture": broadcaster.get_architecture(),
                    "stats": broadcaster.get_current_stats(),
                    "recent_calls": broadcaster.get_recent_calls(10)
                }
            }
            yield f"data: {__import__('json').dumps(initial_data)}\n\n"
            
            # Stream updates
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {__import__('json').dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            broadcaster.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/status/architecture")
async def get_architecture():
    """Get the agent architecture configuration for visualization."""
    broadcaster = get_tool_status_broadcaster()
    return broadcaster.get_architecture()


@app.get("/status/stats")
async def get_stats():
    """Get current session statistics."""
    broadcaster = get_tool_status_broadcaster()
    stats = broadcaster.get_current_stats()
    return stats if stats else {"message": "No active session"}


@app.get("/status/recent")
async def get_recent_calls():
    """Get recent tool calls."""
    broadcaster = get_tool_status_broadcaster()
    return broadcaster.get_recent_calls(20)


# ============================================
# VOICE SETTINGS ENDPOINTS
# ============================================

@app.get("/voice/settings")
async def get_voice_settings():
    """Get current voice settings."""
    manager = get_voice_manager()
    settings = manager.get_current_settings()
    settings["available_voices"] = VOICE_PROFILES
    settings["pace_options"] = PACE_TO_VOICES
    return settings


@app.post("/voice/change")
async def change_voice(request: VoiceChangeRequest):
    """Change the voice to a specific voice ID."""
    manager = get_voice_manager()
    result = manager.change_voice(request.voice_id, request.reason)
    
    if result["success"]:
        # Broadcast the change
        try:
            broadcaster = get_tool_status_broadcaster()
            broadcaster.broadcast_event({
                "type": "voice_change",
                "data": result
            })
        except Exception as e:
            logger.debug(f"Broadcast failed: {e}")
    
    return result


@app.post("/voice/pace")
async def change_pace(request: PaceChangeRequest):
    """Change voice based on pace preference (fast/moderate/slow)."""
    manager = get_voice_manager()
    result = manager.change_pace(request.pace, request.reason)
    
    if result["success"]:
        # Broadcast the change
        try:
            broadcaster = get_tool_status_broadcaster()
            broadcaster.broadcast_event({
                "type": "voice_change",
                "data": result
            })
        except Exception as e:
            logger.debug(f"Broadcast failed: {e}")
    
    return result


@app.post("/voice/instruction")
async def add_instruction(request: PromptInstructionRequest):
    """Add a custom speaking instruction."""
    manager = get_voice_manager()
    result = manager.add_prompt_instruction(request.instruction, request.category)
    
    if result["success"]:
        # Broadcast the change
        try:
            broadcaster = get_tool_status_broadcaster()
            broadcaster.broadcast_event({
                "type": "prompt_update",
                "data": result
            })
        except Exception as e:
            logger.debug(f"Broadcast failed: {e}")
    
    return result


@app.delete("/voice/instructions")
async def clear_instructions():
    """Clear all custom speaking instructions."""
    manager = get_voice_manager()
    result = manager.clear_custom_instructions()
    return result


@app.get("/voice/history")
async def get_voice_history():
    """Get voice change history."""
    manager = get_voice_manager()
    return {"history": manager.change_history}


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "Zero Me - Local Development Server",
        "mode": "development",
        "note": "For production, deploy to Pipecat Cloud instead",
        "endpoints": {
            "/connect": "POST - Create a new voice session (local)",
            "/health": "GET - Health check",
            "/status/stream": "GET - SSE stream for real-time tool status",
            "/status/architecture": "GET - Agent architecture config",
            "/status/stats": "GET - Current session stats",
            "/status/recent": "GET - Recent tool calls",
            "/voice/settings": "GET - Current voice settings",
            "/voice/change": "POST - Change voice ID",
            "/voice/pace": "POST - Change voice pace (fast/moderate/slow)",
            "/voice/instruction": "POST - Add speaking instruction",
            "/voice/instructions": "DELETE - Clear instructions",
            "/voice/history": "GET - Voice change history",
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 50)
    logger.info("LOCAL DEVELOPMENT MODE")
    logger.info("For production, deploy to Pipecat Cloud instead")
    logger.info("=" * 50)
    
    if not DAILY_API_KEY:
        logger.error("DAILY_API_KEY not found in .env.local")
        logger.error("Get your API key from https://dashboard.daily.co/developers")
        logger.error("")
        logger.error("Or deploy to Pipecat Cloud for free integrated Daily:")
        logger.error("  1. pipecat cloud docker build-push")
        logger.error("  2. pipecat cloud deploy")
        logger.error("  3. pipecat cloud agent start zero-me --use-daily")
        sys.exit(1)
    
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        logger.warning("GOOGLE_API_KEY not found - bot will fail to start")
    else:
        logger.info("GOOGLE_API_KEY found")
    
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting local development server on http://localhost:{port}")
    logger.info(f"Connect endpoint: http://localhost:{port}/connect")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

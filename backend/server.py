"""
Connect endpoint server for Pipecat
Handles creating Daily rooms and launching bot sessions

Run with: python server.py
"""
import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv
from loguru import logger

load_dotenv(".env.local")

app = FastAPI(title="Zero Me - Pipecat Connect Server")

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
    
    logger.info(f"Launching bot with Python: {python_path}")
    logger.info(f"Bot script: {bot_script}")
    logger.info(f"Room URL: {room_url}")
    
    # Launch bot process
    process = subprocess.Popen(
        [
            python_path,
            bot_script,
            "--room-url", room_url,
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
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
    """
    logger.info("New connection request")
    
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
    # DailyTransport expects room_url (or url) and token
    return JSONResponse({
        "room_url": room_url,
        "token": user_token,
    })


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "zero-me-pipecat"}


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "Zero Me - Pipecat Voice Assistant",
        "endpoints": {
            "/connect": "POST - Create a new voice session",
            "/health": "GET - Health check",
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    if not DAILY_API_KEY:
        logger.error("DAILY_API_KEY not found in .env.local")
        logger.error("Get your API key from https://dashboard.daily.co/developers")
        sys.exit(1)
    
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        logger.warning("GOOGLE_API_KEY not found - bot will fail to start")
    else:
        logger.info("GOOGLE_API_KEY found")
    
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting Pipecat connect server on http://localhost:{port}")
    logger.info(f"Connect endpoint: http://localhost:{port}/connect")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

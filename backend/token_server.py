"""
Simple token server for development.
Run with: python token_server.py
"""

import os
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from dotenv import load_dotenv
from livekit import api

load_dotenv(".env.local")

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

ROOM_NAME = "zero-me-room"
AGENT_NAME = "Casey-160"  # Must match the agent_name in demo.py


async def create_room_and_dispatch_agent():
    """Create room and dispatch agent to it"""
    lk_api = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

    try:
        # Create room if it doesn't exist
        await lk_api.room.create_room(api.CreateRoomRequest(name=ROOM_NAME))
        print(f"[TokenServer] Room '{ROOM_NAME}' created/exists")
    except Exception as e:
        print(f"[TokenServer] Room create: {e}")

    try:
        # Dispatch agent to room
        await lk_api.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                room=ROOM_NAME,
                agent_name=AGENT_NAME,
            )
        )
        print(f"[TokenServer] Agent '{AGENT_NAME}' dispatched to room")
    except Exception as e:
        print(f"[TokenServer] Agent dispatch: {e}")

    await lk_api.aclose()


class TokenHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Generate a token for the frontend"""
        if self.path.startswith("/token"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Create/dispatch agent to room
            asyncio.run(create_room_and_dispatch_agent())

            # Create token for user
            token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            token.with_identity("user-" + str(os.urandom(4).hex()))
            token.with_name("User")
            token.with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=ROOM_NAME,
                    can_publish=True,
                    can_subscribe=True,
                    agent=False,
                )
            )

            jwt = token.to_jwt()

            response = {
                "token": jwt,
                "url": LIVEKIT_URL,
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[TokenServer] {args[0]}")


def main():
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        print("Error: Missing LIVEKIT_API_KEY or LIVEKIT_API_SECRET in .env.local")
        return

    port = 8080
    server = HTTPServer(("localhost", port), TokenHandler)
    print(f"🔑 Token server running at http://localhost:{port}/token")
    print(f"   LiveKit URL: {LIVEKIT_URL}")
    print()
    server.serve_forever()


if __name__ == "__main__":
    main()

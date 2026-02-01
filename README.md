# zero_me

A floating voice assistant with a cute blob companion. Built with Electron + React frontend and Pipecat backend.

## Structure

```
├── backend/           # Python Pipecat voice agent
│   ├── bot.py         # Pipecat pipeline (STT → LLM → TTS)
│   ├── server.py      # Connect endpoint for sessions
│   ├── requirements.txt
│   ├── start.sh       # Setup venv & run server
│   └── .env.example
│
├── frontend/          # Electron + React app
│   ├── electron/      # Main process & preload
│   ├── src/           # React app
│   │   ├── components/
│   │   │   ├── Dashboard.tsx   # Main control panel
│   │   │   └── Blob.tsx        # Floating blob assistant
│   │   ├── context/
│   │   │   └── AgentContext.tsx  # Pipecat connection state
│   │   └── hooks/
│   │       └── usePipecatAgent.ts  # Pipecat client hook
│   ├── package.json
│   └── start.sh
```

## Features

- **Dashboard**: Minimal, earthy UI with integration placeholders and agent controls
- **Floating Blob**: Cute coral-colored blob that follows you across windows/desktops
  - Changes color based on state (coral=idle, green=listening, purple=speaking)
  - Cute blinking eyes
  - Particle effects and ripples on voice activity
- **Global shortcuts**: `⌘⇧S` Start · `⌘⇧P` Pause · `⌘⇧X` Stop
- **Pipecat integration**: Real-time voice-to-voice agent via Daily WebRTC

## Tech Stack

- **Backend**: Pipecat (Python) with Google STT/TTS and Gemini LLM
- **Frontend**: Electron + React + Pipecat Client SDK
- **Transport**: Daily WebRTC for real-time audio

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- [Daily API Key](https://dashboard.daily.co/developers) (free tier available)
- [Google API Key](https://aistudio.google.com/app/apikey) for Gemini LLM
- [Google Cloud credentials](https://console.cloud.google.com/) for STT/TTS (optional, can use API key)

### Backend Setup

```bash
cd backend

# Copy and configure environment
cp .env.example .env.local
# Edit .env.local with your API keys:
#   DAILY_API_KEY=your-daily-api-key
#   GOOGLE_API_KEY=your-google-api-key

# Run the setup script (creates venv, installs deps, starts server)
./start.sh
```

The server will start at `http://localhost:8080` with:
- `POST /connect` - Creates a voice session (returns Daily room URL + token)
- `GET /health` - Health check

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy and configure environment (optional, defaults to localhost:8080)
cp .env.example .env.local

# Start the Electron app
npm run dev
```

## Architecture

### How It Works

1. **User clicks Start** → Frontend calls `/connect` endpoint
2. **Server creates Daily room** → Launches bot subprocess to join
3. **Frontend joins same room** → Via Pipecat Client SDK + Daily Transport
4. **Voice pipeline runs**:
   - User speaks → Daily captures audio
   - Audio → Google STT → Text
   - Text → Gemini LLM → Response
   - Response → Google TTS → Audio
   - Audio → Daily → User hears response

### Pipecat Pipeline

```
[Daily Input] → [Google STT] → [User Aggregator] → [Gemini LLM] → [Google TTS] → [Daily Output]
```

## Deployment

### Pipecat Cloud (Recommended)

For production, deploy to [Pipecat Cloud](https://pipecat.daily.co):

```bash
# Install CLI
pip install pipecat-cli

# Login and deploy
pipecat cloud login
pipecat cloud docker build-push
pipecat cloud deploy --name zero-me-bot --image your-image-url
```

Then update frontend to use Cloud endpoint:
```
VITE_PIPECAT_CONNECT_ENDPOINT=https://api.pipecat.cloud/v1/agents/zero-me-bot/connect
```

### Self-Hosted

You can also deploy to any cloud provider that runs Python (Fly.io, AWS, GCP, etc.).
See [Pipecat Deployment Docs](https://docs.pipecat.ai/deployment/overview).

## Environment Variables

### Backend (`backend/.env.local`)

| Variable | Description |
|----------|-------------|
| `DAILY_API_KEY` | Daily.co API key for WebRTC rooms |
| `GOOGLE_API_KEY` | Google API key for Gemini LLM |
| `GOOGLE_CREDENTIALS_PATH` | Path to Google Cloud service account JSON (for STT/TTS) |
| `PORT` | Server port (default: 8080) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_PIPECAT_CONNECT_ENDPOINT` | Backend connect URL (default: http://localhost:8080/connect) |

## Resources

- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Pipecat Examples](https://github.com/pipecat-ai/pipecat-examples)
- [Daily WebRTC](https://www.daily.co/)
- [Google Cloud AI](https://cloud.google.com/ai)

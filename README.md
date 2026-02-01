# zero_me

A floating voice assistant with a cute blob companion. Built with Electron + React frontend and Pipecat + Gemini Live backend.

## Features

- **Dashboard**: Minimal, earthy UI with integration placeholders and agent controls
- **Floating Blob**: Cute coral-colored blob that follows you across windows/desktops
  - Changes color based on state (coral=idle, green=listening, purple=speaking)
  - Cute blinking eyes
  - Particle effects and ripples on voice activity
- **Global shortcuts**: `⌘⇧S` Start · `⌘⇧P` Pause · `⌘⇧X` Stop
- **Real-time voice**: Speech-to-speech via Gemini Live with Daily WebRTC

## Tech Stack

- **Backend**: Pipecat (Python) with Gemini Live (native speech-to-speech)
- **Frontend**: Electron + React + Pipecat Client SDK
- **Transport**: Daily WebRTC for real-time audio

## Project Structure

```
├── backend/           # Python Pipecat voice agent
│   ├── bot.py         # Pipecat pipeline (Gemini Live S2S)
│   ├── server.py      # FastAPI server for room management
│   ├── requirements.txt
│   ├── start.sh       # Setup venv & run server
│   └── .env.example
│
├── frontend/          # Electron + React app
│   ├── electron/      # Main process & preload
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx   # Main control panel
│   │   │   └── Blob.tsx        # Floating blob assistant
│   │   ├── context/
│   │   │   └── AgentContext.tsx  # Pipecat connection state
│   │   └── hooks/
│   │       └── usePipecatAgent.ts
│   ├── package.json
│   └── start.sh
```

## Getting Started

### Prerequisites

- Python 3.10+ (not 3.14)
- Node.js 18+
- [Google API Key](https://aistudio.google.com/app/apikey) for Gemini Live
- [Daily API Key](https://dashboard.daily.co/developers) for WebRTC (free tier available)

### 1. Backend Setup

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

The server starts at `http://localhost:8080` with:
- `POST /connect` - Creates a voice session (returns Daily room URL + token)
- `GET /health` - Health check

### 2. Frontend Setup

```bash
cd frontend

# Copy and configure environment
cp .env.example .env.local

# Edit .env.local:
#   VITE_PIPECAT_MODE=local
#   VITE_PIPECAT_CONNECT_ENDPOINT=http://localhost:8080/connect

# Install dependencies
npm install

# Run the app
npm run dev
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Electron)                      │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  Dashboard  │    │  AgentContext    │    │  Floating     │  │
│  │  (React)    │───▶│  (Pipecat SDK)   │───▶│  Blob         │  │
│  └─────────────┘    └────────┬─────────┘    └───────────────┘  │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │ WebRTC (Daily)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Daily.co SFU                                │
│                   (Real-time audio relay)                        │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (Python/Pipecat)                      │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │  server.py  │───▶│  bot.py          │───▶│  Gemini Live  │  │
│  │  (FastAPI)  │    │  (Pipecat)       │    │  (S2S LLM)    │  │
│  └─────────────┘    └──────────────────┘    └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Voice Pipeline

Using Gemini Live for native speech-to-speech:

```
User Voice → Daily WebRTC → Pipecat → Gemini Live (STT+LLM+TTS) → Daily WebRTC → Speaker
```

Gemini Live handles everything in one low-latency service:
- **STT**: Listens to user speech
- **LLM**: Generates response  
- **TTS**: Speaks the response

### Connection Flow

1. **User clicks Start** → Frontend calls `/connect` endpoint
2. **Server creates Daily room** → Launches bot subprocess to join
3. **Frontend joins same room** → Via Pipecat Client SDK + Daily Transport
4. **Voice pipeline runs** → Real-time conversation begins

## Environment Variables

### Backend (`backend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google API key for Gemini Live |
| `DAILY_API_KEY` | Yes | Daily.co API key for WebRTC |
| `PORT` | No | Server port (default: 8080) |
| `ENV` | No | Set to 'local' for development |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_PIPECAT_MODE` | Set to 'local' |
| `VITE_PIPECAT_CONNECT_ENDPOINT` | Backend URL (default: http://localhost:8080/connect) |

## Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘⇧S` / `Ctrl+Shift+S` | Start agent |
| `⌘⇧P` / `Ctrl+Shift+P` | Pause/Resume |
| `⌘⇧X` / `Ctrl+Shift+X` | Stop agent |

## Resources

- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Pipecat Examples](https://github.com/pipecat-ai/pipecat-examples)
- [Daily WebRTC](https://www.daily.co/)
- [Google Gemini](https://ai.google.dev/)

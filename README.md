# zero_me

A floating voice assistant with a cute blob companion. Built with Electron + React frontend and Pipecat backend.

## Structure

```
├── backend/           # Python Pipecat voice agent
│   ├── bot.py         # Pipecat pipeline (Gemini Live speech-to-speech)
│   ├── server.py      # Local development server (optional)
│   ├── Dockerfile     # Pipecat Cloud deployment
│   ├── requirements.txt
│   ├── start.sh       # Setup venv & run locally
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

- **Backend**: Pipecat (Python) with Gemini Live (native speech-to-speech)
- **Frontend**: Electron + React + Pipecat Client SDK
- **Transport**: Daily WebRTC for real-time audio
- **Deployment**: Pipecat Cloud (managed) or self-hosted

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- [Google API Key](https://aistudio.google.com/app/apikey) for Gemini Live

### Option 1: Pipecat Cloud (Recommended)

Pipecat Cloud is the easiest way to deploy - no infrastructure management needed.

#### 1. Create Pipecat Cloud Account

```bash
# Sign up at https://pipecat.daily.co
# Get your API key from the dashboard
```

#### 2. Install Pipecat CLI

```bash
# Install the Pipecat CLI globally using uv (recommended) or pipx
# Requires Python 3.10+

# Using uv (recommended):
uv tool install pipecat-ai-cli

# Or using pipx:
pipx install pipecat-ai-cli

# Verify installation
pipecat --version
```

#### 3. Deploy the Bot

```bash
cd backend

# Copy and configure environment
cp .env.example .env.local
# Edit .env.local with your GOOGLE_API_KEY

# Login to Pipecat Cloud
pipecat cloud auth login

# Build and push Docker image
pipecat cloud docker build-push

# Deploy the agent
pipecat cloud deploy

# Store your Google API key as a secret
pipecat cloud secrets set GOOGLE_API_KEY=your-google-api-key
```

#### 3. Configure Frontend for Cloud

```bash
cd frontend

# Copy and configure environment
cp .env.example .env.local

# Edit .env.local:
#   VITE_PIPECAT_MODE=cloud
#   VITE_PIPECAT_CLOUD_AGENT_NAME=your-agent-name
#   VITE_PIPECAT_CLOUD_API_KEY=pk_your-api-key

# Install and run
npm install
npm run dev
```

### Option 2: Local Development (Self-Hosted)

For testing locally before deploying to Pipecat Cloud.

#### Prerequisites (Local Mode Only)

- [Daily API Key](https://dashboard.daily.co/developers) (free tier available)

#### 1. Backend Setup

```bash
cd backend

# Copy and configure environment
cp .env.example .env.local
# Edit .env.local with your API keys:
#   DAILY_API_KEY=your-daily-api-key
#   GOOGLE_API_KEY=your-google-api-key
#   ENV=local

# Uncomment local dependencies in requirements.txt

# Run the setup script (creates venv, installs deps, starts server)
./start.sh
```

The server will start at `http://localhost:8080` with:
- `POST /connect` - Creates a voice session (returns Daily room URL + token)
- `GET /health` - Health check

#### 2. Frontend Setup (Local Mode)

```bash
cd frontend

# Copy and configure environment
cp .env.example .env.local

# Edit .env.local:
#   VITE_PIPECAT_MODE=local
#   VITE_PIPECAT_CONNECT_ENDPOINT=http://localhost:8080/connect

# Install and run
npm install
npm run dev
```

## Architecture

### How It Works

#### Pipecat Cloud Mode
1. **User clicks Start** → Frontend calls Pipecat Cloud `/start` endpoint
2. **Pipecat Cloud creates Daily room** → Launches bot container automatically
3. **Frontend joins room** → Via Pipecat Client SDK + Daily Transport
4. **Voice pipeline runs** (see below)

#### Local Mode
1. **User clicks Start** → Frontend calls local `/connect` endpoint
2. **Server creates Daily room** → Launches bot subprocess to join
3. **Frontend joins same room** → Via Pipecat Client SDK + Daily Transport
4. **Voice pipeline runs** (see below)

### Voice Pipeline

Using Gemini Live for native speech-to-speech:

```
[Daily Audio Input] → [VAD] → [Gemini Live (STT+LLM+TTS)] → [Daily Audio Output]
```

Gemini Live handles:
- Speech-to-Text (STT) - listens to user speech
- LLM processing - generates response
- Text-to-Speech (TTS) - speaks the response

All in one service with low latency!

## Deployment Comparison

| Feature | Pipecat Cloud | Self-Hosted |
|---------|--------------|-------------|
| Daily API Key | Integrated (free 1:1 voice) | Required |
| Infrastructure | Managed | Your responsibility |
| Scaling | Automatic | Manual |
| Krisp Noise Cancellation | Included | Not available |
| Setup | 3 CLI commands | Server + bot management |

## Environment Variables

### Backend (`backend/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google API key for Gemini Live |
| `PIPECAT_CLOUD_API_KEY` | Cloud only | Pipecat Cloud API key |
| `DAILY_API_KEY` | Local only | Daily.co API key for WebRTC |
| `ENV` | Local only | Set to 'local' for development |
| `PORT` | No | Server port (default: 8080) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_PIPECAT_MODE` | 'cloud' or 'local' (default: cloud) |
| `VITE_PIPECAT_CLOUD_AGENT_NAME` | Your Pipecat Cloud agent name |
| `VITE_PIPECAT_CLOUD_API_KEY` | Pipecat Cloud API key |
| `VITE_PIPECAT_CONNECT_ENDPOINT` | Local server URL (local mode only) |

## CLI Commands (Pipecat Cloud)

```bash
# Install CLI (using uv or pipx)
uv tool install pipecat-ai-cli
# or: pipx install pipecat-ai-cli

# Verify installation
pipecat --version

# Login to Pipecat Cloud
pipecat cloud auth login

# Build and push Docker image
pipecat cloud docker build-push

# Deploy agent (reads pcc-deploy.toml if present)
pipecat cloud deploy

# Deploy with specific options
pipecat cloud deploy my-agent my-image:latest --region us-west

# Set secrets
pipecat cloud secrets set GOOGLE_API_KEY=your-key

# Check agent status
pipecat cloud agent status my-agent-name

# Monitor live sessions
pipecat tail

# Delete a deployment
pipecat cloud agent delete my-agent-name
```

## Resources

- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Pipecat Cloud](https://docs.pipecat.ai/deployment/pipecat-cloud/introduction)
- [Pipecat Examples](https://github.com/pipecat-ai/pipecat-examples)
- [Daily WebRTC](https://www.daily.co/)
- [Google Gemini](https://ai.google.dev/)

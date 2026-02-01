# zero_me

A floating voice assistant with a cute blob companion. Built with Electron + React frontend and LiveKit Agents backend.

## Structure

```
├── backend/           # Python LiveKit voice agent
│   ├── demo.py        # Main agent code
│   ├── requirements.txt
│   ├── start.sh       # Setup venv & run agent
│   └── .env.example
│
├── frontend/          # Electron + React app
│   ├── electron/      # Main process & preload
│   ├── src/           # React app
│   │   ├── components/
│   │   │   ├── Dashboard.tsx   # Main control panel
│   │   │   └── Blob.tsx        # Floating blob assistant
│   │   └── hooks/
│   │       └── useLiveKitAgent.ts  # LiveKit connection
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
- **LiveKit integration**: Voice-to-voice agent connection

## Getting Started

### Backend

```bash
cd backend
cp .env.example .env.local
# Fill in your LiveKit credentials in .env.local
./start.sh
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Requirements

- **Backend**: Python 3.9+
- **Frontend**: Node.js 18+
- **LiveKit Cloud account** (or self-hosted LiveKit server)


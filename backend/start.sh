#!/bin/bash
set -e

cd "$(dirname "$0")"

# Check for .env.local FIRST
if [ ! -f ".env.local" ]; then
  echo ""
  echo "⚠️  .env.local not found!"
  echo ""
  echo "Create it with your LiveKit credentials:"
  echo "  cp .env.example .env.local"
  echo ""
  echo "Then fill in your values:"
  echo "  LIVEKIT_URL=wss://your-project.livekit.cloud"
  echo "  LIVEKIT_API_KEY=your_api_key"
  echo "  LIVEKIT_API_SECRET=your_api_secret"
  echo ""
  exit 1
fi

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt

# Start the agent
echo ""
echo "Starting LiveKit agent..."
python demo.py start

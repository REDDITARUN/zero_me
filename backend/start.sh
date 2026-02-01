#!/bin/bash
# Start script for Pipecat backend

set -e

cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Zero Me - Pipecat Backend${NC}"
echo ""

# Find a compatible Python version (3.10-3.13)
# Pipecat dependencies (numba/silero) don't support Python 3.14+
PYTHON_CMD=""
for py in python3.12 python3.11 python3.13 python3.10; do
    if command -v "$py" &> /dev/null; then
        PYTHON_CMD="$py"
        break
    fi
done

# Fallback to python3 if no specific version found
if [ -z "$PYTHON_CMD" ]; then
    PYTHON_CMD="python3"
fi

# Check Python version
PY_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

echo "Using Python: $PYTHON_CMD (version $PY_VERSION)"

if [ "$PY_MAJOR" -ne 3 ] || [ "$PY_MINOR" -lt 10 ] || [ "$PY_MINOR" -gt 13 ]; then
    echo -e "${RED}Error: Python 3.10-3.13 is required (found $PY_VERSION)${NC}"
    echo "Please install Python 3.12: brew install python@3.12"
    exit 1
fi

# Check for .env.local
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}Warning: .env.local not found${NC}"
    echo "Creating from .env.example..."
    cp .env.example .env.local
    echo -e "${RED}Please edit .env.local with your API keys:${NC}"
    echo "  - DAILY_API_KEY: Get from https://dashboard.daily.co/developers"
    echo "  - GOOGLE_API_KEY: Get from https://aistudio.google.com/app/apikey"
    echo ""
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo -e "${GREEN}Dependencies installed!${NC}"
echo ""

# Start the server
echo -e "${GREEN}Starting connect server...${NC}"
echo "Connect endpoint will be available at: http://localhost:8080/connect"
echo ""

python server.py

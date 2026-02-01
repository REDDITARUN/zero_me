#!/bin/bash
# Start script for Pipecat backend with LangChain agents

set -e

cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Zero Me - Voice Agent Backend        ║${NC}"
echo -e "${GREEN}║   Pipecat + LangChain Multi-Agent        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
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

echo -e "${BLUE}Using Python: $PYTHON_CMD (version $PY_VERSION)${NC}"

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
    echo "  Required:"
    echo "    - DAILY_API_KEY: https://dashboard.daily.co/developers"
    echo "    - GOOGLE_API_KEY: https://aistudio.google.com/app/apikey"
    echo "  Optional (for integrations):"
    echo "    - NOTION_TOKEN: https://www.notion.so/my-integrations"
    echo "    - RESEND_API_KEY: https://resend.com/api-keys"
    echo "    - WANDB_API_KEY: https://wandb.ai/settings"
    echo ""
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Creating virtual environment with $PYTHON_CMD...${NC}"
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo -e "${GREEN}✓ Dependencies installed!${NC}"
echo ""

# Check for optional services
echo -e "${BLUE}Checking integrations...${NC}"

# Check Redis
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis is running${NC}"
    else
        echo -e "${YELLOW}⚠ Redis installed but not running (memory features disabled)${NC}"
        echo "  Start with: brew services start redis"
    fi
else
    echo -e "${YELLOW}⚠ Redis not installed (memory features disabled)${NC}"
    echo "  Install with: brew install redis"
fi

# Check environment variables
source .env.local 2>/dev/null || true

if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}✗ GOOGLE_API_KEY not set${NC}"
else
    echo -e "${GREEN}✓ GOOGLE_API_KEY configured${NC}"
fi

if [ -z "$DAILY_API_KEY" ]; then
    echo -e "${RED}✗ DAILY_API_KEY not set${NC}"
else
    echo -e "${GREEN}✓ DAILY_API_KEY configured${NC}"
fi

if [ -z "$NOTION_TOKEN" ]; then
    echo -e "${YELLOW}⚠ NOTION_TOKEN not set (Doc/Todo/Calendar disabled)${NC}"
else
    echo -e "${GREEN}✓ NOTION_TOKEN configured${NC}"
fi

if [ -z "$RESEND_API_KEY" ]; then
    echo -e "${YELLOW}⚠ RESEND_API_KEY not set (Email disabled)${NC}"
else
    echo -e "${GREEN}✓ RESEND_API_KEY configured${NC}"
fi

if [ -z "$WANDB_API_KEY" ]; then
    echo -e "${YELLOW}⚠ WANDB_API_KEY not set (Analytics disabled)${NC}"
else
    echo -e "${GREEN}✓ WANDB_API_KEY configured${NC}"
fi

echo ""

# Start the server
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Starting Server...               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "Endpoints:"
echo "  - Connect: http://localhost:8080/connect"
echo "  - Health:  http://localhost:8080/health"
echo ""
echo "Agent Architecture:"
echo "  - Voice Agent (Gemini Live)"
echo "  - Main Dispatcher Agent"
echo "  - Sub-Agents: Doc, Todo, Email, Calendar"
echo "  - Personality Enhancer Agent"
echo ""

python server.py

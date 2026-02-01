#!/bin/bash
set -e

cd "$(dirname "$0")"

# Check for node_modules
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Start in development mode
echo "Starting Electron app in dev mode..."
npm run dev

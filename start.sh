#!/usr/bin/env bash
# start.sh — universal launcher for LifeOS Bot
# Usage:
#   chmod +x start.sh
#   ./start.sh

set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  LifeOS Telegram Bot Launcher"
echo "========================================"

# 1. Bootstrap virtualenv if missing
if [ ! -d "venv" ]; then
  echo ">> Creating virtualenv..."
  python3 -m venv venv || true
fi

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

# 2. Install requirements
echo ">> Checking dependencies..."
pip install -r requirements.txt --quiet --no-warn-script-location

# 3. Bootstrap .env on first run
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo ">> .env not found — copying from .env.example"
  cp .env.example .env
fi

mkdir -p data logs credentials

# 4. Launch bot
echo ">> Starting bot via app.py..."
exec python3 app.py

#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# LifeOS Bot — Termux (Android) setup script
# Usage:
#   bash setup_termux.sh
# ============================================================
set -e

echo "================================================"
echo " LifeOS Bot — Termux setup"
echo "================================================"

if [ ! -d /data/data/com.termux ]; then
    echo "ERROR: this script is meant for Termux only."
    echo "On Linux VPS, simply run: ./start.sh or pip install -r requirements.txt"
    exit 1
fi

pkg install -y python rust binutils patchelf make libffi openssl
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
fi

mkdir -p data logs credentials
echo "Setup completed! Run bot with: python3 app.py"

#!/usr/bin/env python3
"""
Universal entry point wrapper for LifeOS Bot (Pterodactyl / VPS / Container / Termux).
Executes bot.main via asyncio.run().
"""
from __future__ import annotations

import asyncio
import sys

from bot.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] LifeOS Bot stopped by user.")
        sys.exit(0)

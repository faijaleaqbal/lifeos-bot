#!/usr/bin/env python3
"""
LifeOS Diagnostics & Integration Doctor
Validates SQLite database, Telegram connectivity, OpenWeatherMap API, Google Sheets, and Notion configurations.
"""
import asyncio
import os
import sys
from pathlib import Path
from bot.config import settings
from bot.database.init_db import init_db
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def run_diagnostics():
    print("==================================================")
    print("       LIFEOS BOT COMPREHENSIVE DIAGNOSTICS       ")
    print("==================================================")
    results = {}

    # 1. Database Integrity Check
    print("\n[1/5] Checking SQLite Database Integrity...")
    try:
        await init_db()
        engine = create_async_engine(settings.database_url, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            val = res.scalar()
            if val == 1:
                print("  ✓ SQLite database connected and operational.")
                results["Database"] = "PASSED"
        await engine.dispose()
    except Exception as e:
        print(f"  ✗ SQLite error: {e}")
        results["Database"] = f"FAILED: {e}"

    # 2. Telegram Bot Token Check
    print("\n[2/5] Checking Telegram Bot Connectivity...")
    if not settings.bot_token:
        print("  ✗ BOT_TOKEN is empty in .env")
        results["Telegram"] = "NOT CONFIGURED"
    else:
        try:
            import urllib.request, json
            req = urllib.request.Request(f"https://api.telegram.org/bot{settings.bot_token}/getMe")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                username = data.get("result", {}).get("username")
                print(f"  ✓ Connected to Telegram as @{username}")
                results["Telegram"] = f"PASSED (@{username})"
        except urllib.error.HTTPError as e:
            print(f"  ✗ Telegram HTTP {e.code}: {e.reason} (Token may be unauthorized/revoked)")
            results["Telegram"] = f"FAILED (HTTP {e.code})"
        except Exception as e:
            print(f"  ✗ Telegram connection failed: {e}")
            results["Telegram"] = f"FAILED: {e}"

    # 3. OpenWeather API Check
    print("\n[3/5] Checking Weather Integration...")
    if not settings.openweather_api_key:
        print(f"  ⚠ OpenWeather API key not configured (Default city: {settings.weather_city})")
        results["Weather"] = "OPTIONAL / NOT CONFIGURED"
    else:
        try:
            from bot.services.weather import get_weather
            w = await get_weather(settings.weather_city)
            if w:
                print(f"  ✓ Weather live for {settings.weather_city}: {w.get('temp', 'N/A')}°C, {w.get('description', '')}")
                results["Weather"] = "PASSED"
            else:
                print("  ⚠ Weather returned empty payload")
                results["Weather"] = "WARNING (Empty)"
        except Exception as e:
            print(f"  ✗ Weather check failed: {e}")
            results["Weather"] = f"FAILED: {e}"

    # 4. Notion API Check
    print("\n[4/5] Checking Notion Integration...")
    if not settings.notion_token or not settings.notion_database_id:
        print("  ⚠ Notion token or database ID not configured (Quick capture disabled)")
        results["Notion"] = "OPTIONAL / NOT CONFIGURED"
    else:
        try:
            from bot.services.notion import capture_to_notion
            print("  ✓ Notion configuration detected.")
            results["Notion"] = "CONFIGURED"
        except Exception as e:
            print(f"  ✗ Notion check failed: {e}")
            results["Notion"] = f"FAILED: {e}"

    # 5. Google Sheets Check
    print("\n[5/5] Checking Google Sheets Sync...")
    if not settings.google_sheets_id or not settings.google_sheets_credentials_file.exists():
        print("  ⚠ Google Sheets credentials or Sheet ID not found (Local SQLite will store expenses)")
        results["Google Sheets"] = "OPTIONAL (Local SQLite Fallback Active)"
    else:
        print(f"  ✓ Google Sheets credentials found at {settings.google_sheets_credentials_file}")
        results["Google Sheets"] = "CONFIGURED"

    print("\n---------------- DIAGNOSTICS SUMMARY ----------------")
    for k, v in results.items():
        print(f"  {k:15}: {v}")
    print("=====================================================")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())

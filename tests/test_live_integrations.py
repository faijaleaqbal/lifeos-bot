import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
load_dotenv(PROJECT_ROOT / ".env")

async def test_google_sheets():
    print("\n--- Testing Google Sheets Connection ---")
    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials/google_sheets.json")
    sheet_id = os.getenv("GOOGLE_SHEETS_ID", "")
    
    full_creds_path = PROJECT_ROOT / creds_file if not Path(creds_file).is_absolute() else Path(creds_file)
    
    if not full_creds_path.exists():
        print(f"❌ Credentials file not found at: {full_creds_path}")
        return False
    
    if not sheet_id:
        print("❌ GOOGLE_SHEETS_ID is not set in .env")
        return False

    try:
        from bot.services.sheets import check_sheet_access
        print(f"Checking access to sheet ID: {sheet_id} ...")
        title = await check_sheet_access(sheet_id)
        if title:
            print(f"✅ Successfully connected to Google Sheet! Title: \"{title}\"")
            return True
        else:
            print("❌ Failed to access Google Sheet. Please check service account permissions (Share -> Editor).")
            return False
    except Exception as e:
        print(f"❌ Error during Google Sheets test: {e}")
        return False

async def test_notion():
    print("\n--- Testing Notion Connection ---")
    token = os.getenv("NOTION_TOKEN", "")
    db_id = os.getenv("NOTION_DATABASE_ID", "")
    
    if not token:
        print("❌ NOTION_TOKEN is not set in .env")
        return False
    
    if not db_id:
        print("❌ NOTION_DATABASE_ID is not set in .env")
        return False

    try:
        from notion_client import Client
        client = Client(auth=token)
        print(f"Querying Notion database ID: {db_id} ...")
        loop = asyncio.get_event_loop()
        db = await loop.run_in_executor(None, lambda: client.databases.retrieve(database_id=db_id))
        
        title_objs = db.get("title", [])
        title = "".join([t.get("plain_text", "") for t in title_objs]) if title_objs else "Untitled Database"
        print(f"✅ Successfully connected to Notion Database! Title: \"{title}\"")
        
        properties = db.get("properties", {})
        if "Name" in properties:
            print("✅ Found expected 'Name' title column in Notion database.")
        else:
            print(f"⚠️  Note: LifeOS bot looks for a title column named 'Name'. Found properties: {list(properties.keys())}")
            
        return True
    except Exception as e:
        print(f"❌ Notion test failed: {e}")
        print("💡 Hint: Ensure you shared the database with the integration ('...' menu -> 'Connect to' -> select integration).")
        return False

async def test_weather():
    print("\n--- Testing OpenWeatherMap Connection ---")
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    city = os.getenv("WEATHER_CITY", "Malda,IN")
    
    if not api_key:
        print("❌ OPENWEATHER_API_KEY is not set in .env")
        return False

    try:
        from bot.services.weather import get_weather, format_weather
        print(f"Fetching weather for: {city} ...")
        w = await get_weather(city=city, api_key=api_key)
        if w and "error" not in w:
            print(f"✅ Successfully fetched weather for {w['city']}, {w.get('country')}!")
            print("Formatted output:")
            print(format_weather(w))
            return True
        else:
            err = w.get("error") if w else "Unknown error"
            print(f"❌ Failed to fetch weather: {err}")
            return False
    except Exception as e:
        print(f"❌ Error during weather test: {e}")
        return False

async def test_news():
    print("\n--- Testing NewsAPI Connection ---")
    api_key = os.getenv("NEWS_API_KEY", "")
    
    if not api_key:
        print("❌ NEWS_API_KEY is not set in .env")
        return False

    try:
        from bot.services.news import get_tech_news, format_news
        print("Fetching top tech headlines ...")
        news = await get_tech_news(api_key=api_key, page_size=3)
        if news and "error" not in news and news.get("articles"):
            print(f"✅ Successfully fetched {len(news['articles'])} tech news articles!")
            print("Formatted output:")
            print(format_news(news))
            return True
        else:
            err = news.get("error") if news else "No articles returned"
            print(f"❌ Failed to fetch tech news: {err}")
            return False
    except Exception as e:
        print(f"❌ Error during news test: {e}")
        return False

async def main():
    weather_ok = await test_weather()
    news_ok = await test_news()
    sheets_ok = await test_google_sheets()
    notion_ok = await test_notion()
    
    print("\n==============================")
    print(f"Weather (OpenWeather): {'✅ READY' if weather_ok else '❌ NOT READY'}")
    print(f"Tech News (NewsAPI):   {'✅ READY' if news_ok else '❌ NOT READY'}")
    print(f"Google Sheets:         {'✅ READY' if sheets_ok else '❌ NOT READY'}")
    print(f"Notion:                {'✅ READY' if notion_ok else '❌ NOT READY'}")
    print("==============================\n")

if __name__ == "__main__":
    asyncio.run(main())


"""Weather service — fetch weather from OpenWeatherMap API."""
import asyncio
import logging
import httpx
from bot.config import settings

logger = logging.getLogger(__name__)

async def get_weather(city: str = None, api_key: str = None):
    """
    Fetch current weather from OpenWeatherMap.
    Returns dict: {temp, feels_like, description, humidity, wind_speed, city, icon}
    """
    city = city or settings.weather_city
    api_key = api_key or settings.openweather_api_key
    
    if not api_key:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": city,
                    "appid": api_key,
                    "units": "metric",
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "temp": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "description": data["weather"][0]["description"].title(),
                "icon": data["weather"][0]["icon"],
                "humidity": data["main"]["humidity"],
                "wind_speed": round(data["wind"]["speed"]),
                "city": data["name"],
                "country": data["sys"]["country"],
            }
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
        return None

async def get_weather_emoji(icon: str):
    """Map OpenWeather icon to emoji."""
    emoji_map = {
        "01d": "☀️", "01n": "🌙",
        "02d": "🌤", "02n": "☁️",
        "03d": "☁️", "03n": "☁️",
        "04d": "☁️", "04n": "☁️",
        "09d": "🌧", "09n": "🌧",
        "10d": "🌦", "10n": "🌧",
        "11d": "⛈", "11n": "⛈",
        "13d": "❄️", "13n": "❄️",
        "50d": "🌫", "50n": "🌫",
    }
    return emoji_map.get(icon, "🌡")

def format_weather(w: dict) -> str:
    """Format weather dict into Telegram message."""
    emoji = "☀️"
    icon_map = {
        "01d": "☀️", "01n": "🌙", "02d": "🌤", "02n": "☁️",
        "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️",
        "09d": "🌧", "09n": "🌧", "10d": "🌦", "10n": "🌧",
        "11d": "⛈", "11n": "⛈", "13d": "❄️", "13n": "❄️",
        "50d": "🌫", "50n": "🌫",
    }
    emoji = icon_map.get(w.get("icon", ""), "🌡")
    
    text = (
        f"🌤 <b>Weather — {w['city']}, {w['country']}</b>\n"
        f"{emoji} <b>{w['temp']}°C</b> (feels like {w['feels_like']}°C)\n"
        f"📝 {w['description']}\n"
        f"💧 Humidity: {w['humidity']}%\n"
        f"💨 Wind: {w['wind_speed']} m/s"
    )
    return text
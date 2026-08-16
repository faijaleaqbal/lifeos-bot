"""Weather service — fetch weather from OpenWeatherMap API."""
import html
import logging
import httpx
from bot.config import settings

logger = logging.getLogger(__name__)

async def get_weather(city: str = None, api_key: str = None) -> dict | None:
    """
    Fetch current weather from OpenWeatherMap.
    Returns dict: {temp, feels_like, description, humidity, wind_speed, city, country, icon} or {"error": msg}
    """
    city = city if city else settings.weather_city
    api_key = settings.openweather_api_key if api_key is None else api_key
    
    if not api_key:
        return {"error": "API key not configured"}
    
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
            if response.status_code == 401:
                logger.error("OpenWeatherMap authentication failed (401)")
                return {"error": "Invalid API key"}
            elif response.status_code == 404:
                logger.error(f"OpenWeatherMap city '{city}' not found (404)")
                return {"error": f"City '{city}' not found"}
            elif response.status_code == 429:
                logger.error("OpenWeatherMap rate limit exceeded (429)")
                return {"error": "Rate limit exceeded"}
                
            response.raise_for_status()
            data = response.json()
            
            return {
                "temp": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "description": data["weather"][0]["description"].capitalize(),
                "icon": data["weather"][0]["icon"],
                "humidity": data["main"]["humidity"],
                "wind_speed": round(data.get("wind", {}).get("speed", 0)),
                "city": data.get("name", city),
                "country": data.get("sys", {}).get("country", ""),
            }
    except httpx.TimeoutException:
        logger.error("Weather fetch timed out")
        return {"error": "Request timed out"}
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
        return {"error": "Unable to fetch weather data"}

def format_weather(w: dict) -> str:
    """Format weather dict into Telegram message matching brief style."""
    if not w:
        return "🌤 <b>Weather:</b>\n   Add OPENWEATHER_API_KEY in .env for live weather"
        
    if "error" in w:
        return f"🌤 <b>Weather:</b>\n   Weather unavailable ({html.escape(w['error'])})"
        
    icon_map = {
        "01d": "☀️", "01n": "🌙",
        "02d": "🌤", "02n": "☁️",
        "03d": "⛅", "03n": "☁️",
        "04d": "☁️", "04n": "☁️",
        "09d": "🌧", "09n": "🌧",
        "10d": "🌦", "10n": "🌧",
        "11d": "⛈", "11n": "⛈",
        "13d": "❄️", "13n": "❄️",
        "50d": "🌫", "50n": "🌫",
    }
    emoji = icon_map.get(w.get("icon", ""), "🌡")
    city_str = f"{w['city']}, {w['country']}" if w.get('country') else w['city']
    
    return (
        f"🌤 <b>Weather ({html.escape(city_str)}):</b>\n"
        f"   {emoji} <b>{w['temp']}°C</b>, {html.escape(w['description'])} (feels like {w['feels_like']}°C) • 💧 {w['humidity']}% humidity"
    )
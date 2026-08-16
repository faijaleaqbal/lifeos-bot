import html
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.config import settings
from bot.database.crud import get_or_create_user
from bot.services.weather import get_weather, format_weather
from bot.services.news import get_tech_news, format_news

router = Router()

@router.message(Command("setcity"))
async def cmd_setcity(message: Message, session, state: FSMContext):
    """Set the user's default city for weather forecasts."""
    await state.clear()
    args = message.text.partition(" ")[2].strip()
    
    if not args:
        await message.answer(
            "📍 <b>Set Your City</b>\n\n"
            "Usage: <code>/setcity &lt;city name&gt;</code>\n"
            "Example: <code>/setcity Kolkata,IN</code> or <code>/setcity Malda</code>\n\n"
            "Your weather updates in /weather and /morning will use this location."
        )
        return
        
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    user.city = args
    await session.commit()
    
    await message.answer(f"✅ City set to <b>{html.escape(args)}</b>. Your weather updates will use this location.")

@router.message(Command("weather"))
async def cmd_weather(message: Message, session, state: FSMContext):
    """Get current weather for user's configured city or a one-off specified city."""
    await state.clear()
    args = message.text.partition(" ")[2].strip()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    
    if args:
        # One-off override for specified city (doesn't save to DB)
        weather = await get_weather(city=args)
        await message.answer(format_weather(weather))
    else:
        # Use user's saved city or global fallback
        has_custom_city = bool(user.city and user.city.strip())
        city_to_fetch = user.city if has_custom_city else settings.weather_city
        weather = await get_weather(city=city_to_fetch)
        weather_text = format_weather(weather)
        
        if not has_custom_city:
            weather_text += "\n\n💡 <i>Set your city with <code>/setcity &lt;city name&gt;</code> for personalized weather.</i>"
            
        await message.answer(weather_text)

@router.message(Command("brief", "morning"))
async def cmd_brief(message: Message, session, state: FSMContext):
    """Generate daily morning briefing."""
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    
    now = datetime.now()
    
    text = f"📊 <b>Morning Brief — {now.strftime('%A, %B %d')}</b>\n\n"
    
    # === Weather ===
    has_custom_city = bool(user.city and user.city.strip())
    city_to_fetch = user.city if has_custom_city else settings.weather_city
    weather = await get_weather(city=city_to_fetch)
    weather_text = format_weather(weather)
    
    if not has_custom_city:
        weather_text += "\n   <i>💡 Set your city with /setcity <city name> for personalized weather.</i>"
        
    text += weather_text + "\n\n"
    
    # === Calendar (placeholder) ===
    text += "📅 <b>Today's Events:</b>\n"
    text += "   No events (Connect Google Calendar in /settings)\n\n"
    
    # === Tasks (placeholder) ===
    text += "📝 <b>Top 3 Tasks:</b>\n"
    text += "   Not set. Use /capture to add tasks.\n\n"
    
    # === Tech News ===
    news = await get_tech_news()
    text += format_news(news) + "\n\n"
    
    text += "💡 <i>Configure integrations in /settings for full briefing.</i>"
    
    await message.answer(text)
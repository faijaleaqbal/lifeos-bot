from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.crud import get_or_create_user
from bot.services.weather import get_weather, format_weather

router = Router()

@router.message(Command("brief"))
async def cmd_brief(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    now = datetime.now()
    
    text = f"📊 <b>Morning Brief — {now.strftime('%A, %B %d')}</b>\n\n"
    
    # === Weather ===
    weather = await get_weather()
    if weather:
        text += format_weather(weather) + "\n\n"
    else:
        text += "🌤 <b>Weather:</b>\n   Add OPENWEATHER_API_KEY in /settings for live weather\n\n"
    
    # === Calendar (placeholder) ===
    text += "📅 <b>Today's Events:</b>\n"
    text += "   No events (Connect Google Calendar in /settings)\n\n"
    
    # === Tasks (placeholder) ===
    text += "📝 <b>Top 3 Tasks:</b>\n"
    text += "   Not set. Use /capture to add tasks.\n\n"
    
    # === Tech News (placeholder) ===
    text += "📰 <b>Tech News:</b>\n"
    text += "   (News integration coming soon)\n\n"
    
    text += "💡 <i>Configure integrations in /settings for full briefing.</i>"
    
    await message.answer(text)
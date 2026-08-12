from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.crud import get_or_create_user

router = Router()

@router.message(Command("brief"))
async def cmd_brief(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    from datetime import datetime
    now = datetime.now()
    
    text = f"📊 <b>Morning Brief — {now.strftime('%A, %B %d')}</b>\n\n"
    
    # Weather (placeholder — needs OpenWeather API key)
    text += "🌤 <b>Weather:</b>\n"
    text += f"   ☀️ Malda, IN\n"
    text += f"   (Connect OpenWeather API key in .env for live data)\n\n"
    
    # Calendar (placeholder)
    text += "📅 <b>Today's Events:</b>\n"
    text += "   No events (Connect Google Calendar in /settings)\n\n"
    
    # Tasks (placeholder)
    text += "📝 <b>Top 3 Tasks:</b>\n"
    text += "   Not set. Use /capture to add tasks.\n\n"
    
    # News (placeholder)
    text += "📰 <b>Tech News:</b>\n"
    text += "   (News integration coming soon)\n\n"
    
    text += "💡 <i>Configure integrations in /settings for full briefing.</i>"
    
    await message.answer(text)
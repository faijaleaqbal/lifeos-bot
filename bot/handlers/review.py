from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database.crud import get_or_create_user, add_journal_entry

router = Router()

class ReviewStates(StatesGroup):
    waiting_mood = State()
    waiting_win = State()
    waiting_improvement = State()

@router.message(Command("review"))
async def cmd_review(message: Message, state: FSMContext):
    await state.clear()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{i}️⃣", callback_data=f"mood_{i}") for i in range(1, 11)]])
    
    await message.answer(
        "🌙 <b>Daily Review</b>\n\n"
        "How was your day? (1-10)",
        reply_markup=kb
    )
    await state.set_state(ReviewStates.waiting_mood)

@router.callback_query(ReviewStates.waiting_mood, F.data.startswith("mood_"))
async def process_mood(callback: CallbackQuery, state: FSMContext):
    mood = int(callback.data.split("_")[1])
    await state.update_data(mood=mood)
    await callback.message.edit_text(f"🌙 Mood: {mood}/10\n\nWhat was your <b>one win</b> today?")
    await state.set_state(ReviewStates.waiting_win)

@router.message(ReviewStates.waiting_win)
async def process_win(message: Message, state: FSMContext):
    win = message.text.strip()
    await state.update_data(win=win)
    await message.answer("🌙 What's <b>one thing to improve</b> tomorrow?")
    await state.set_state(ReviewStates.waiting_improvement)

@router.message(ReviewStates.waiting_improvement)
async def process_improvement(message: Message, state: FSMContext, session):
    improvement = message.text.strip()
    data = await state.get_data()
    
    user = await get_or_create_user(session, message.from_user.id)
    entry = await add_journal_entry(
        session, user.id,
        mood_score=data.get("mood"),
        win=data.get("win", ""),
        improvement=improvement
    )
    
    await message.answer(
        f"✅ <b>Daily Review Saved!</b>\n\n"
        f"🌙 Mood: {data.get('mood')}/10\n"
        f"🏆 Win: {data.get('win')}\n"
        f"📈 Improve: {improvement}\n\n"
        f"Good night! 🌙"
    )
    await state.clear()
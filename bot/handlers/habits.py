from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database.crud import get_or_create_user, add_habit, get_habits, get_habit, complete_habit, get_habit_completions
from bot.keyboards.inline import get_habit_done_keyboard, get_habit_list_keyboard

router = Router()

class HabitStates(StatesGroup):
    waiting_name = State()
    waiting_frequency = State()
    waiting_time = State()

@router.message(Command("habit"))
async def cmd_habit(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    args = message.text.replace("/habit", "", 1).strip()
    
    if args.startswith("add"):
        await message.answer(
            "🎯 <b>New Habit</b>\n\n"
            "Send me the habit name:\n"
            "Example: <code>Morning Run</code>"
        )
        await state.set_state(HabitStates.waiting_name)
        return
    
    if args.startswith("list") or not args:
        habits = await get_habits(session, user.id)
        if not habits:
            await message.answer("🎯 No habits yet. Use <code>/habit add</code> to create one.")
            return
        
        text = "🎯 <b>Your Habits</b>\n\n"
        for h in habits:
            text += f"• {'🟢' if h.active else '🔴'} <b>{h.name}</b>\n"
            text += f"   Streak: {h.streak_current}🔥 (best: {h.streak_longest})\n"
            text += f"   Frequency: {h.frequency}"
            if h.reminder_time:
                text += f" at {h.reminder_time}"
            text += "\n\n"
        
        await message.answer(text)
        return

@router.message(HabitStates.waiting_name)
async def process_habit_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Daily", callback_data="freq_daily")
    builder.button(text="📆 Weekdays", callback_data="freq_weekdays")
    builder.button(text="📊 Custom", callback_data="freq_custom")
    builder.adjust(1)
    
    await message.answer(
        f"✅ Habit: <b>{name}</b>\n\n"
        "How often?",
        reply_markup=builder.as_markup()
    )
    await state.set_state(HabitStates.waiting_frequency)

@router.callback_query(HabitStates.waiting_frequency, F.data.startswith("freq_"))
async def process_habit_freq(callback: CallbackQuery, state: FSMContext, session):
    freq = callback.data[5:]  # Remove "freq_"
    
    if freq == "custom":
        await callback.message.answer("Send me the frequency (e.g. <code>mon,wed,fri</code>):")
        await state.set_state(HabitStates.waiting_time)
        await state.update_data(frequency="custom")
        return
    
    await state.update_data(frequency=freq)
    await callback.message.answer("⏰ Send reminder time (e.g. <code>06:30</code>) or send <code>none</code> for no reminder:")
    await state.set_state(HabitStates.waiting_time)

@router.message(HabitStates.waiting_time)
async def process_habit_time(message: Message, state: FSMContext, session):
    time_input = message.text.strip()
    data = await state.get_data()
    name = data.get("name", "Habit")
    frequency = data.get("frequency", "daily")
    
    reminder_time = None
    if time_input.lower() != "none":
        reminder_time = time_input
    
    user = await get_or_create_user(session, message.from_user.id)
    habit = await add_habit(session, user.id, name, frequency, reminder_time)
    
    await message.answer(
        f"✅ <b>Habit created!</b>\n\n"
        f"🎯 {habit.name}\n"
        f"📅 {habit.frequency}\n"
        f"⏰ Reminder: {reminder_time or 'None'}\n\n"
        f"Use <code>/done \"{habit.name}\"</code> to mark complete."
    )
    await state.clear()

@router.message(Command("done"))
async def cmd_done(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    name = message.text.replace("/done", "", 1).strip().strip('"').strip("'")
    
    if not name:
        habits = await get_habits(session, user.id)
        if not habits:
            await message.answer("No habits to mark done.")
            return
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for h in habits:
            builder.button(text=f"✅ {h.name}", callback_data=f"habit_done:{h.id}")
        builder.adjust(1)
        await message.answer("Which habit did you complete?", reply_markup=builder.as_markup())
        return
    
    habits = await get_habits(session, user.id)
    for h in habits:
        if h.name.lower() == name.lower():
            try:
                completion = await complete_habit(session, h.id)
                await message.answer(
                    f"✅ <b>{h.name}</b> marked done!\n\n"
                    f"🔥 Current streak: {h.streak_current}\n"
                    f"🏆 Best streak: {h.streak_longest}"
                )
            except Exception as e:
                await message.answer(f"❌ Already completed today or error: {e}")
            return
    
    await message.answer(f"❌ Habit '{name}' not found. Use <code>/habit list</code> to see your habits.")

@router.callback_query(F.data.startswith("habit_done:"))
async def cb_habit_done(callback: CallbackQuery, session):
    habit_id = int(callback.data.split(":")[1])
    try:
        habit = await get_habit(session, habit_id)
        if not habit:
            await callback.answer("Habit not found")
            return
        completion = await complete_habit(session, habit_id)
        await callback.message.edit_text(
            f"✅ <b>{habit.name}</b> marked done!\n\n"
            f"🔥 Current streak: {habit.streak_current}\n"
            f"🏆 Best streak: {habit.streak_longest}"
        )
    except Exception as e:
        await callback.answer(f"Error: {e}")

@router.message(Command("habits"))
async def cmd_habits(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    habits = await get_habits(session, user.id)
    
    if not habits:
        await message.answer("🎯 No habits yet. Use <code>/habit add</code> to create one.")
        return
    
    text = "📅 <b>Habit Streaks</b>\n\n"
    for h in habits:
        text += f"{'🟢' if h.active else '🔴'} <b>{h.name}</b>\n"
        text += f"   🔥 {h.streak_current} streak"
        text += f" (🏆 best: {h.streak_longest})\n\n"
    
    await message.answer(text)
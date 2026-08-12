from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database.crud import get_or_create_user
from bot.keyboards.inline import get_settings_keyboard

router = Router()

class SetupStates(StatesGroup):
    waiting_notion_token = State()
    waiting_notion_db = State()
    waiting_sheets_id = State()
    waiting_timezone = State()

# ===== Bot Menu Commands (for Telegram BotFather) =====
BOT_COMMANDS = [
    ("start", "🏠 Start bot & see welcome"),
    ("help", "📖 Show all commands"),
    ("brief", "🌅 Morning briefing (weather, tasks, habits)"),
    ("spent", "💰 Log expense (e.g. /spent 120 coffee)"),
    ("report", "📊 Expense report with chart (week/month)"),
    ("habit", "🎯 Manage habits (add/list)"),
    ("done", "✅ Mark habit complete"),
    ("habits", "📅 Habit streak grid + chart"),
    ("remind", "⏰ Set reminder (e.g. /remind 10m \"Call\")"),
    ("reminders", "📋 List active reminders"),
    ("cancel", "❌ Cancel reminder by ID"),
    ("capture", "📝 Save to Notion (or forward any msg)"),
    ("review", "🌙 Evening review (mood + win + improve)"),
    ("settings", "⚙️ Configure Notion, Sheets, Timezone"),
]

@router.message(CommandStart())
async def cmd_start(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    
    text = (
        f"👋 Welcome to <b>LifeOS</b>, {message.from_user.first_name}!\n\n"
        "Your personal daily operating system on Telegram.\n\n"
        "<b>🚀 Quick Start:</b>\n"
        "1️⃣ <code>/settings</code> — Connect Notion & Google Sheets\n"
        "2️⃣ <code>/brief</code> — See morning briefing\n"
        "3️⃣ <code>/spent 120 coffee</code> — Log first expense\n"
        "4️⃣ <code>/habit add</code> — Create a habit\n"
        "5️⃣ <code>/remind 10m \"Test\"</code> — Set a reminder\n\n"
        "<b>📋 All Commands:</b> Use <code>/help</code> for full list.\n\n"
        "Forward any message to save it to Notion automatically."
    )
    
    if not user.notion_token or not user.google_sheets_id:
        text += "\n\n⚠️ <b>Setup needed:</b> Use /settings to connect Notion & Google Sheets."
    
    await message.answer(text)

@router.message(Command("help"))
async def cmd_help(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id)
    
    text = (
        "<b>📖 LifeOS — All Commands</b>\n\n"
        "<b>🏠 Basics</b>\n"
        "  /start — Welcome & quick start\n"
        "  /help — This message\n"
        "  /settings — Configure integrations\n\n"
        "<b>💰 Expenses</b>\n"
        "  /spent 120 coffee — Log ₹120 (cat: food)\n"
        "  /spent 500 uber --cat transport\n"
        "  /report week — Last 7 days + chart\n"
        "  /report month — Last 30 days + chart\n\n"
        "<b>🎯 Habits</b>\n"
        "  /habit add — Create habit (interactive)\n"
        "  /habit list — List all habits\n"
        "  /done \"Run\" — Mark habit complete\n"
        "  /habits — Streak grid + chart (90 days)\n\n"
        "<b>⏰ Reminders</b>\n"
        "  /remind 10m \"Call mom\" — In 10 min\n"
        "  /remind 2h \"Meeting\" — In 2 hours\n"
        "  /remind tomorrow 9am \"Standup\"\n"
        "  /remind every friday 5pm \"Report\"\n"
        "  /reminders — List all active\n"
        "  /cancel 3 — Cancel reminder #3\n\n"
        "<b>📝 Capture & Review</b>\n"
        "  /capture \"Idea\" — Save to Notion\n"
        "  (Forward any message to capture)\n"
        "  /review — Evening review (mood + win)\n\n"
        "<b>🌅 Daily Briefing</b>\n"
        "  /brief — Morning brief (weather, tasks)\n\n"
        "<b>⚙️ Settings</b>\n"
        "  /settings — Notion, Sheets, Timezone\n"
    )
    
    if user.notion_token or user.google_sheets_id:
        text += (
            f"\n<b>📦 Your Setup:</b>\n"
            f"  Notion: {'✅' if user.notion_token else '❌'}\n"
            f"  Sheets: {'✅' if user.google_sheets_id else '❌'}\n"
            f"  Timezone: {user.timezone}"
        )
    
    text += "\n\n<i>💡 Tip: Forward any message to save it instantly!</i>"
    
    await message.answer(text)

@router.message(Command("settings"))
async def cmd_settings(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id)
    
    notion_status = "✅ Connected" if user.notion_token else "❌ Not connected"
    sheets_status = "✅ Connected" if user.google_sheets_id else "❌ Not connected"
    tz_status = f"🌍 {user.timezone}"
    
    text = (
        "<b>⚙️ Settings</b>\n\n"
        f"📝 Notion: {notion_status}\n"
        f"📊 Google Sheets: {sheets_status}\n"
        f"{tz_status}\n\n"
        "Tap a button to configure:"
    )
    
    await message.answer(text, reply_markup=get_settings_keyboard())

# ===== Notion Setup =====
@router.callback_query(F.data == "setup_notion")
async def cb_setup_notion(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 <b>Notion Setup</b>\n\n"
        "1. Go to <a href='https://www.notion.so/my-integrations'>Notion Integrations</a>\n"
        "2. Create new integration → Copy <b>Internal Integration Token</b>\n"
        "3. Share your database with the integration\n"
        "4. Copy the <b>Database ID</b> from URL\n\n"
        "Send me the <b>Integration Token</b> first:"
    )
    await state.set_state(SetupStates.waiting_notion_token)

@router.message(SetupStates.waiting_notion_token)
async def process_notion_token(message: Message, state: FSMContext, session):
    user = await get_or_create_user(session, message.from_user.id)
    user.notion_token = message.text.strip()
    await session.commit()
    await message.answer("✅ Token saved! Now send the <b>Database ID</b>:")
    await state.set_state(SetupStates.waiting_notion_db)

@router.message(SetupStates.waiting_notion_db)
async def process_notion_db(message: Message, state: FSMContext, session):
    user = await get_or_create_user(session, message.from_user.id)
    user.notion_db_id = message.text.strip()
    await session.commit()
    await message.answer("✅ Notion connected! Use /settings to verify.", reply_markup=get_settings_keyboard())
    await state.clear()

# ===== Google Sheets Setup =====
@router.callback_query(F.data == "setup_sheets")
async def cb_setup_sheets(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📊 <b>Google Sheets Setup</b>\n\n"
        "1. Create a Google Sheet with columns: Date, Amount (₹), Category, Description\n"
        "2. Create Service Account in Google Cloud Console\n"
        "3. Download JSON credentials → save as <code>credentials/google_sheets.json</code>\n"
        "4. Share the sheet with the service account email\n"
        "5. Copy the <b>Sheet ID</b> from URL\n\n"
        "Send me the <b>Sheet ID</b>:"
    )
    await state.set_state(SetupStates.waiting_sheets_id)

@router.message(SetupStates.waiting_sheets_id)
async def process_sheets_id(message: Message, state: FSMContext, session):
    user = await get_or_create_user(session, message.from_user.id)
    user.google_sheets_id = message.text.strip()
    await session.commit()
    await message.answer("✅ Google Sheets connected! Use /settings to verify.", reply_markup=get_settings_keyboard())
    await state.clear()

# ===== Timezone Setup =====
@router.callback_query(F.data == "setup_timezone")
async def cb_setup_timezone(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇮🇳 India (IST)", callback_data="tz_india")],
        [InlineKeyboardButton(text="🇺🇸 UTC", callback_data="tz_utc")],
        [InlineKeyboardButton(text="🇬🇧 London (GMT)", callback_data="tz_london")],
        [InlineKeyboardButton(text="🇺🇸 New York (EST)", callback_data="tz_newyork")],
        [InlineKeyboardButton(text="🇦🇪 Dubai (GST)", callback_data="tz_dubai")],
        [InlineKeyboardButton(text="🇸🇬 Singapore (SGT)", callback_data="tz_singapore")],
        [InlineKeyboardButton(text="⌨️ Type custom", callback_data="tz_custom")],
    ])
    await callback.message.edit_text(
        "🌍 <b>Select your timezone:</b>\n\n"
        "Or type a custom timezone (e.g. <code>Asia/Kolkata</code>):",
        reply_markup=kb
    )
    await state.set_state(SetupStates.waiting_timezone)

@router.callback_query(F.data.startswith("tz_"))
async def cb_set_timezone(callback: CallbackQuery, state: FSMContext, session):
    tz_raw = callback.data[3:]
    
    tz_map = {
        "india": "Asia/Kolkata",
        "utc": "UTC",
        "london": "Europe/London",
        "newyork": "America/New_York",
        "dubai": "Asia/Dubai",
        "singapore": "Asia/Singapore",
        "custom": "custom",
    }
    
    tz = tz_map.get(tz_raw, tz_raw)
    
    if tz == "custom":
        await callback.message.answer("⌨️ Send me your timezone (e.g. <code>Asia/Kolkata</code>):")
        await state.set_state(SetupStates.waiting_timezone)
        return
    
    user = await get_or_create_user(session, callback.from_user.id)
    user.timezone = tz
    await session.commit()
    await callback.message.edit_text(f"✅ Timezone set to <b>{tz}</b>!\n\nUse /settings to verify.")
    await state.clear()

@router.message(SetupStates.waiting_timezone)
async def process_custom_timezone(message: Message, state: FSMContext, session):
    tz = message.text.strip()
    user = await get_or_create_user(session, message.from_user.id)
    user.timezone = tz
    await session.commit()
    await message.answer(f"✅ Timezone set to <b>{tz}</b>!\n\nUse /settings to verify.", reply_markup=get_settings_keyboard())
    await state.clear()

# Note: /cancel command is handled in reminders.py (handles both FSM cancel + reminder cancel)
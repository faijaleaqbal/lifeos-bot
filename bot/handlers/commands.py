import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database.crud import get_or_create_user
from bot.keyboards.inline import get_settings_keyboard
from bot.services.sheets import get_service_account_email, check_sheet_access
from bot.services.notion import verify_notion_access

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
    ("brief", "🌅 Morning briefing (weather, news, tasks)"),
    ("weather", "🌤 Check current weather"),
    ("setcity", "📍 Set your city for weather"),
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
        "2️⃣ <code>/setcity Kolkata,IN</code> — Set your city for weather\n"
        "3️⃣ <code>/brief</code> — See morning briefing\n"
        "4️⃣ <code>/spent 120 coffee</code> — Log first expense\n"
        "5️⃣ <code>/habit add</code> — Create a habit\n"
        "6️⃣ <code>/remind 10m \"Test\"</code> — Set a reminder\n\n"
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
        "<b>🌅 Daily Briefing & Weather</b>\n"
        "  /brief — Morning brief (weather, news, tasks)\n"
        "  /weather — Current weather (or /weather <city>)\n"
        "  /setcity <city> — Set your city for weather\n\n"
        "<b>⚙️ Settings</b>\n"
        "  /settings — Notion, Sheets, Timezone\n"
    )
    
    city_display = user.city if user.city else "Not set (using default)"
    text += (
        f"\n<b>📦 Your Setup:</b>\n"
        f"  City: {city_display}\n"
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
        "1. Go to <a href='https://www.notion.so/profile/integrations'>Notion My Integrations</a>\n"
        "2. Create a new integration → Copy your <b>Internal Integration Token</b>\n"
        "3. Share your database with the integration (click '...' on database page → 'Connect to' / 'Add connections')\n"
        "4. Copy your <b>Database ID</b> or full database URL\n\n"
        "Send me your <b>Integration Token</b> (starts with <code>ntn_</code> or <code>secret_</code>):"
    )
    await state.set_state(SetupStates.waiting_notion_token)

@router.message(SetupStates.waiting_notion_token)
async def process_notion_token(message: Message, state: FSMContext, session):
    token = message.text.strip()
    user = await get_or_create_user(session, message.from_user.id)
    user.notion_token = token
    await session.commit()
    await message.answer(
        "✅ Token saved!\n\n"
        "Now send your <b>Database ID</b> (or paste the full Notion database URL):"
    )
    await state.set_state(SetupStates.waiting_notion_db)

@router.message(SetupStates.waiting_notion_db)
async def process_notion_db(message: Message, state: FSMContext, session):
    raw_input = message.text.strip()
    user = await get_or_create_user(session, message.from_user.id)
    
    # Extract 32-character database ID if URL was provided
    db_id = raw_input
    clean_hex = raw_input.replace("-", "")
    hex_match = re.search(r'([a-f0-9]{32})', clean_hex)
    if hex_match:
        db_id = hex_match.group(1)
        
    await message.answer("🔄 <i>Testing connection to your Notion database...</i>")
    
    success, result = await verify_notion_access(user.notion_token, db_id)
    if success:
        user.notion_db_id = db_id
        await session.commit()
        await message.answer(
            f"✅ <b>Notion connected successfully!</b>\n\n"
            f"📝 <b>Database:</b> {result}\n"
            f"🆔 <b>ID:</b> <code>{db_id}</code>\n\n"
            f"You can now use /capture or forward messages to save them to Notion.",
            reply_markup=get_settings_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            f"❌ <b>Notion connection failed.</b>\n\n"
            f"Error details: <code>{result}</code>\n\n"
            f"<b>Troubleshooting:</b>\n"
            f"1. Open your Notion database in browser/app.\n"
            f"2. Click <b>...</b> in top-right → <b>Connect to</b> → select your integration.\n"
            f"3. Ensure the token and database ID are correct.\n\n"
            f"Send the Database ID again, or tap /settings to start over."
        )

# ===== Google Sheets Setup =====
@router.callback_query(F.data == "setup_sheets")
async def cb_setup_sheets(callback: CallbackQuery, state: FSMContext):
    sa_email = get_service_account_email()
    if sa_email:
        sa_instruction = (
            f"2. <b>Share your sheet</b> with Editor permissions to:\n"
            f"<code>{sa_email}</code>\n"
            f"<i>(Tap to copy email)</i>"
        )
    else:
        sa_instruction = "2. Share your sheet with the bot's Service Account email (Editor permissions)."

    await callback.message.edit_text(
        f"📊 <b>Google Sheets Setup</b>\n\n"
        f"1. Create a Google Sheet with headers: <code>Date | Amount | Category | Description</code>\n"
        f"{sa_instruction}\n"
        f"3. Copy the <b>Sheet ID</b> (or full URL) from your browser.\n\n"
        f"Send me your <b>Sheet ID</b> or <b>Google Sheet URL</b>:"
    )
    await state.set_state(SetupStates.waiting_sheets_id)

@router.message(SetupStates.waiting_sheets_id)
async def process_sheets_id(message: Message, state: FSMContext, session):
    raw_input = message.text.strip()
    user = await get_or_create_user(session, message.from_user.id)
    
    # Extract sheet ID if full URL was pasted
    sheet_id = raw_input
    url_match = re.search(r'/d/([a-zA-Z0-9-_]+)', raw_input)
    if url_match:
        sheet_id = url_match.group(1)
        
    await message.answer("🔄 <i>Testing connection to your Google Sheet...</i>")
    
    title = await check_sheet_access(sheet_id)
    if title:
        user.google_sheets_id = sheet_id
        await session.commit()
        await message.answer(
            f"✅ <b>Google Sheet connected successfully!</b>\n\n"
            f"📊 <b>Sheet Title:</b> {title}\n"
            f"🆔 <b>Sheet ID:</b> <code>{sheet_id}</code>\n\n"
            f"Expenses logged with /spent will now sync to this sheet.",
            reply_markup=get_settings_keyboard()
        )
        await state.clear()
    else:
        sa_email = get_service_account_email()
        sa_hint = f"<code>{sa_email}</code>" if sa_email else "the service account email"
        await message.answer(
            f"❌ <b>Could not access Google Sheet.</b>\n\n"
            f"<b>Troubleshooting:</b>\n"
            f"1. Open your sheet and click <b>Share</b>.\n"
            f"2. Add {sa_hint} as an <b>Editor</b>.\n"
            f"3. Check that the Sheet ID/URL is correct.\n\n"
            f"Send the Sheet ID or URL again, or tap /settings to start over."
        )

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
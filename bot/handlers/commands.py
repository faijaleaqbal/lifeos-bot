from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
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

@router.message(CommandStart())
async def cmd_start(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
    
    text = (
        f"👋 Welcome to <b>LifeOS</b>, {message.from_user.first_name}!\n\n"
        "Your personal daily operating system on Telegram.\n\n"
        "<b>Quick commands:</b>\n"
        "📊 <code>/brief</code> — Morning briefing (weather, calendar, tasks, news)\n"
        "💰 <code>/spent 120 coffee</code> — Log expense\n"
        "📈 <code>/report week</code> — Expense report with chart\n"
        "🎯 <code>/habit add \"Run\"</code> — Create habit\n"
        "✅ <code>/done \"Run\"</code> — Mark habit complete\n"
        "📅 <code>/habits</code> — Visual streak grid\n"
        "⏰ <code>/remind 10m \"Call mom\"</code> — Set reminder\n"
        "📝 <code>/capture \"Idea\"</code> — Save to Notion\n"
        "🌙 <code>/review</code> — Daily evening review\n"
        "⚙️ <code>/settings</code> — Configure integrations\n\n"
        "Forward any message to save it to Notion automatically."
    )
    
    if not user.notion_token or not user.google_sheets_id:
        text += "\n\n⚠️ <b>Setup needed:</b> Use /settings to connect Notion & Google Sheets."
    
    await message.answer(text)

@router.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message, None)

@router.message(Command("settings"))
async def cmd_settings(message: Message, session):
    user = await get_or_create_user(session, message.from_user.id)
    
    status = []
    status.append(f"🟢 Notion: {'Connected' if user.notion_token else 'Not connected'}")
    status.append(f"🟢 Google Sheets: {'Connected' if user.google_sheets_id else 'Not connected'}")
    status.append(f"🟢 Timezone: {user.timezone}")
    
    text = (
        "<b>⚙️ Settings</b>\n\n"
        + "\n".join(status)
        + "\n\nTap a button to configure:"
    )
    
    await message.answer(text, reply_markup=get_settings_keyboard())

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
    await message.answer("✅ Notion connected! Use /settings to verify.")
    await state.clear()

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
    await message.answer("✅ Google Sheets connected! Make sure credentials file is in place.")
    await state.clear()
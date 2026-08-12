from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.crud import get_or_create_user, add_capture
from bot.services.notion import create_notion_page

router = Router()

@router.message(Command("capture"))
async def cmd_capture(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    text = message.text.replace("/capture", "", 1).strip()
    
    if not text:
        await message.answer(
            "📝 <b>Quick Capture</b>\n\n"
            "Usage: <code>/capture Buy domain for project</code>\n\n"
            "Or just forward any message to me — I'll save it to Notion!"
        )
        return
    
    # Save locally
    await add_capture(session, user.id, text, source="command")
    
    # Sync to Notion if configured
    notion_status = "💾 Saved locally (connect Notion in /settings)"
    if user.notion_token and user.notion_db_id:
        title = text[:100] + ("..." if len(text) > 100 else "")
        page_url = await create_notion_page(
            user.notion_token, user.notion_db_id, title, content=text
        )
        if page_url:
            notion_status = f"📤 Saved to Notion: {page_url}"
        else:
            notion_status = "⚠️ Notion sync failed — saved locally"
    
    await message.answer(f"✅ <b>Captured!</b>\n\n📝 {text}\n\n{notion_status}")

# Forward handler — saves forwarded messages
@router.message(F.forward_date)
async def handle_forward(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    content = message.text or message.caption or "Non-text message"
    
    # Save locally
    await add_capture(session, user.id, content, source="forward")
    
    # Sync to Notion if configured
    notion_status = "💾 Saved locally (connect Notion in /settings)"
    if user.notion_token and user.notion_db_id:
        title = content[:100] + ("..." if len(content) > 100 else "")
        page_url = await create_notion_page(
            user.notion_token, user.notion_db_id, title, content=content
        )
        if page_url:
            notion_status = f"📤 Saved to Notion: {page_url}"
        else:
            notion_status = "⚠️ Notion sync failed — saved locally"
    
    preview = content[:100] + ("..." if len(content) > 100 else "")
    await message.answer(f"✅ <b>Forwarded message captured!</b>\n\n📝 {preview}\n\n{notion_status}")
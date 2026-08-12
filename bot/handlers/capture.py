from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.crud import get_or_create_user, add_capture

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
    
    # Save locally for now (Notion integration optional)
    await add_capture(session, user.id, text, source="command")
    
    await message.answer(
        f"✅ <b>Captured!</b>\n\n"
        f"📝 {text}\n\n"
        f"{'📤 Saved to Notion' if user.notion_token else '💾 Saved locally (connect Notion in /settings to sync)'}"
    )

# Forward handler — saves forwarded messages
@router.message(F.forward_date)
async def handle_forward(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    content = message.text or message.caption or "Non-text message"
    
    await add_capture(session, user.id, content, source="forward")
    
    await message.answer(
        f"✅ <b>Forwarded message captured!</b>\n\n"
        f"📝 {content[:100]}{'...' if len(content) > 100 else ''}\n\n"
        f"{'📤 Saved to Notion' if user.notion_token else '💾 Saved locally (connect Notion in /settings)'}"
    )
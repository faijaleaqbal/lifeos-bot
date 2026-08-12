import re
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.crud import get_or_create_user, add_reminder, get_active_reminders, deactivate_reminder
from bot.keyboards.inline import get_reminder_cancel_keyboard

router = Router()

def parse_time(text: str):
    """Parse natural language time → (trigger_at, cron_expr or None)"""
    text = text.strip().lower()
    now = datetime.now()
    
    # "10m" or "10min" → minutes from now
    m = re.match(r'^(\d+)\s*m(?:in)?$', text)
    if m:
        return now + timedelta(minutes=int(m.group(1))), None
    
    # "2h" or "2hours" → hours from now
    h = re.match(r'^(\d+)\s*h(?:ours?)?$', text)
    if h:
        return now + timedelta(hours=int(h.group(1))), None
    
    # "tomorrow" or "tomorrow 9am"
    if text.startswith("tomorrow"):
        tomorrow = now + timedelta(days=1)
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3)
            if ampm == "pm" and hour != 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
            return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0), None
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0), None
    
    # "every mon 9am" or "every friday 5pm" → cron
    day_map = {
        "mon": "MON", "monday": "MON",
        "tue": "TUE", "tuesday": "TUE",
        "wed": "WED", "wednesday": "WED",
        "thu": "THU", "thursday": "THU",
        "fri": "FRI", "friday": "FRI",
        "sat": "SAT", "saturday": "SAT",
        "sun": "SUN", "sunday": "SUN",
    }
    
    every_match = re.match(r'^every\s+(\w+)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$', text)
    if every_match:
        day = every_match.group(1).lower()
        if day in day_map:
            hour = int(every_match.group(2))
            minute = int(every_match.group(3)) if every_match.group(3) else 0
            ampm = every_match.group(4)
            if ampm == "pm" and hour != 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
            cron = f"{minute} {hour} * * {day_map[day]}"
            return now, cron
    
    return None, None

@router.message(Command("remind"))
async def cmd_remind(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    text = message.text.replace("/remind", "", 1).strip()
    
    if not text:
        await message.answer(
            "⏰ <b>Reminders</b>\n\n"
            "Usage:\n"
            "<code>/remind 10m \"Call mom\"</code> — 10 min from now\n"
            "<code>/remind 2h \"Meeting prep\"</code> — 2 hours from now\n"
            "<code>/remind tomorrow 9am \"Team standup\"</code>\n"
            "<code>/remind every friday 5pm \"Weekly report\"</code>"
        )
        return
    
    # Extract quoted message
    msg_match = re.search(r'"([^"]+)"', text)
    if not msg_match:
        await message.answer('❌ Please wrap your reminder text in quotes.\nExample: <code>/remind 10m "Call mom"</code>')
        return
    
    reminder_text = msg_match.group(1)
    time_part = text.replace(msg_match.group(0), "").strip()
    
    trigger_at, cron = parse_time(time_part)
    
    if trigger_at is None:
        await message.answer(
            f"❌ Could not parse time: <code>{time_part}</code>\n\n"
            "Supported formats:\n"
            "• <code>10m</code> — minutes from now\n"
            "• <code>2h</code> — hours from now\n"
            "• <code>tomorrow 9am</code>\n"
            "• <code>every friday 5pm</code>"
        )
        return
    
    import uuid
    job_id = str(uuid.uuid4())
    reminder = await add_reminder(session, user.id, reminder_text, trigger_at, cron, job_id)
    
    if cron:
        await message.answer(
            f"✅ <b>Recurring reminder set!</b>\n\n"
            f"⏰ Every: <code>{cron}</code>\n"
            f"📝 {reminder_text}"
        )
    else:
        await message.answer(
            f"✅ <b>Reminder set!</b>\n\n"
            f"⏰ When: {trigger_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"📝 {reminder_text}"
        )

@router.message(Command("reminders"))
async def cmd_reminders(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    reminders = await get_active_reminders(session, user.id)
    
    if not reminders:
        await message.answer("⏰ No active reminders.\n\nUse <code>/remind 10m \"Call mom\"</code> to set one.")
        return
    
    text = "⏰ <b>Active Reminders</b>\n\n"
    for r in reminders:
        recurring = f"🔄 {r.recurring_cron}" if r.recurring_cron else f"📅 {r.trigger_at.strftime('%m/%d %H:%M')}"
        text += f"#{r.id} — {reminder_text_display(r)}\n"
        text += f"   {recurring}\n"
        text += f"   Use <code>/cancel {r.id}</code> to remove\n\n"
    
    await message.answer(text)

def reminder_text_display(r):
    return f"📝 {r.message[:40]}"

@router.message(Command("cancel"))
async def cmd_cancel_reminder(message: Message, session, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id)
    
    args = message.text.replace("/cancel", "", 1).strip()
    
    if not args.isdigit():
        await message.answer("❌ Usage: <code>/cancel 3</code> (use the reminder ID from <code>/reminders</code>)")
        return
    
    reminder_id = int(args)
    success = await deactivate_reminder(session, reminder_id)
    
    if success:
        await message.answer(f"✅ Reminder #{reminder_id} cancelled.")
    else:
        await message.answer(f"❌ Reminder #{reminder_id} not found.")
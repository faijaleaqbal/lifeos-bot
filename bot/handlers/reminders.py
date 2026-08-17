import re
import logging
from datetime import datetime, timedelta
import pytz
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.crud import get_or_create_user, add_reminder, get_active_reminders, deactivate_reminder
from bot.keyboards.inline import get_reminder_cancel_keyboard
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router()

def parse_time(text: str, user_tz_name: str = "Asia/Kolkata"):
    """Parse natural language time in user's timezone → (trigger_at naive local, cron_expr or None)"""
    text = text.strip().lower()
    try:
        tz = pytz.timezone(user_tz_name)
    except Exception:
        tz = pytz.timezone(settings.timezone)
        
    now = datetime.now(tz)
    
    # "10m" or "10min" → minutes from now
    m = re.match(r'^(\d+)\s*m(?:in)?$', text)
    if m:
        target = now + timedelta(minutes=int(m.group(1)))
        return target.replace(tzinfo=None), None
    
    # "2h" or "2hours" → hours from now
    h = re.match(r'^(\d+)\s*h(?:ours?)?$', text)
    if h:
        target = now + timedelta(hours=int(h.group(1)))
        return target.replace(tzinfo=None), None

    # "1d" or "2days" or "2d" → days from now
    d = re.match(r'^(\d+)\s*d(?:ays?)?$', text)
    if d:
        target = now + timedelta(days=int(d.group(1)))
        return target.replace(tzinfo=None), None
    
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
            target = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return target.replace(tzinfo=None), None
        target = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        return target.replace(tzinfo=None), None
    
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
            return now.replace(tzinfo=None), cron
    
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
            "<code>/remind 10m Call mom</code> — 10 min from now\n"
            "<code>/remind 2h Meeting prep</code> — 2 hours from now\n"
            "<code>/remind tomorrow 9am Team standup</code>\n"
            "<code>/remind every friday 5pm Weekly report</code>"
        )
        return
    
    # Extract reminder message and time part (supports both quoted and unquoted formats)
    msg_match = re.search(r'["\'](.*?)["\']', text)
    if msg_match:
        reminder_text = msg_match.group(1).strip()
        time_part = text.replace(msg_match.group(0), "").strip()
    else:
        # Check multi-word time patterns first (e.g., 'every friday 5pm', 'tomorrow 9am')
        multi_word_match = re.match(
            r'^(every\s+\w+\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|tomorrow(?:\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?)\s+(.+)$',
            text,
            re.IGNORECASE
        )
        if multi_word_match:
            time_part = multi_word_match.group(1).strip()
            reminder_text = multi_word_match.group(2).strip()
        else:
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                time_part = parts[0].strip()
                reminder_text = parts[1].strip()
            else:
                time_part = parts[0].strip()
                reminder_text = ""

    reminder_text = reminder_text.strip('\'"')

    if not reminder_text:
        await message.answer("❌ Please provide a reminder message.\nExample: <code>/remind 10m Call mom</code>")
        return
    
    user_tz = user.timezone if (user and user.timezone) else settings.timezone
    trigger_at, cron = parse_time(time_part, user_tz)
    
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
    
    # Add to APScheduler live
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from bot.services.scheduler import fire_reminder
    
    scheduler = getattr(message.bot, "scheduler", None)
    if scheduler:
        if cron:
            try:
                scheduler.add_job(
                    fire_reminder,
                    CronTrigger.from_crontab(cron, timezone=user_tz),
                    args=[message.bot, user.id, reminder_text, reminder.id],
                    id=f"reminder_{reminder.id}",
                    replace_existing=True,
                )
            except Exception as e:
                logger.error(f"Live scheduler add failed: {e}")
        else:
            try:
                scheduler.add_job(
                    fire_reminder,
                    DateTrigger(run_date=trigger_at, timezone=user_tz),
                    args=[message.bot, user.id, reminder_text, reminder.id],
                    id=f"reminder_{reminder.id}",
                    replace_existing=True,
                )
            except Exception as e:
                logger.error(f"Live scheduler add failed: {e}")
    
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
        await message.answer("⏰ No active reminders.\n\nUse <code>/remind 10m Call mom</code> to set one.")
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
    
    # If numeric — cancel a reminder
    if args.isdigit():
        reminder_id = int(args)
        success = await deactivate_reminder(session, reminder_id)
        
        # Remove from scheduler
        scheduler = getattr(message.bot, "scheduler", None)
        if scheduler:
            try:
                scheduler.remove_job(f"reminder_{reminder_id}")
            except Exception:
                pass  # Job may not exist
        
        if success:
            await message.answer(f"✅ Reminder #{reminder_id} cancelled.")
        else:
            await message.answer(f"❌ Reminder #{reminder_id} not found.")
        return
    
    # Otherwise — cancel FSM
    current = await state.get_state()
    if current is None:
        await message.answer("Nothing to cancel. Use /cancel <reminder_id> to cancel a reminder.")
        return
    
    await state.clear()
    await message.answer("❌ Cancelled.")
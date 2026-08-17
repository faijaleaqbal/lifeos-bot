"""APScheduler setup — real reminder firing + daily brief + review prompts."""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, and_
import httpx

from bot.config import settings
from bot.database.models import User, Reminder, Habit
from bot.services.weather import get_weather, format_weather

logger = logging.getLogger(__name__)

async def setup_scheduler(scheduler: AsyncIOScheduler, bot):
    """Setup all scheduled jobs on startup."""
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # === 1. Morning Brief — 7 AM daily ===
    scheduler.add_job(
        send_morning_brief,
        CronTrigger(hour=7, minute=0, timezone=settings.timezone),
        args=[bot, async_session_maker],
        id="morning_brief",
        replace_existing=True,
    )
    logger.info("Scheduled morning brief at 7 AM")
    
    # === 2. Evening Review — 9 PM daily ===
    scheduler.add_job(
        send_evening_review,
        CronTrigger(hour=21, minute=0, timezone=settings.timezone),
        args=[bot, async_session_maker],
        id="evening_review",
        replace_existing=True,
    )
    logger.info("Scheduled evening review at 9 PM")
    
    # === 3. Load persisted reminders from DB ===
    async with async_session_maker() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.active == True)
        )
        reminders = result.scalars().all()
        
        for rem in reminders:
            if rem.recurring_cron:
                try:
                    scheduler.add_job(
                        fire_reminder,
                        CronTrigger.from_crontab(rem.recurring_cron, timezone=settings.timezone),
                        args=[bot, rem.user_id, rem.message, rem.id],
                        id=f"reminder_{rem.id}",
                        replace_existing=True,
                    )
                except Exception as e:
                    logger.error(f"Failed to load recurring reminder {rem.id}: {e}")
            else:
                # One-time reminder — only if in future
                import pytz
                tz = pytz.timezone(settings.timezone)
                now_local = datetime.now(tz).replace(tzinfo=None)
                if rem.trigger_at > now_local:
                    scheduler.add_job(
                        fire_reminder,
                        DateTrigger(run_date=rem.trigger_at, timezone=settings.timezone),
                        args=[bot, rem.user_id, rem.message, rem.id],
                        id=f"reminder_{rem.id}",
                        replace_existing=True,
                    )
    
    logger.info(f"Loaded {len(reminders)} reminders from DB")
    
    # === 4. Habit reminders ===
    async with async_session_maker() as session:
        result = await session.execute(
            select(Habit).where(Habit.active == True).where(Habit.reminder_time.isnot(None))
        )
        habits = result.scalars().all()
        
        for habit in habits:
            if habit.reminder_time:
                try:
                    hour, minute = habit.reminder_time.split(":")
                    scheduler.add_job(
                        send_habit_reminder,
                        CronTrigger(hour=int(hour), minute=int(minute), timezone=settings.timezone),
                        args=[bot, habit.user_id, habit.id, habit.name],
                        id=f"habit_reminder_{habit.id}",
                        replace_existing=True,
                    )
                except Exception as e:
                    logger.error(f"Failed to load habit reminder {habit.id}: {e}")
        
        logger.info(f"Loaded {len(habits)} habit reminders")
    
    # === 5. Data cleanup — daily at 2 AM ===
    scheduler.add_job(
        cleanup_old_data,
        CronTrigger(hour=2, minute=0, timezone=settings.timezone),
        args=[async_session_maker],
        id="data_cleanup",
        replace_existing=True,
    )
    logger.info("Scheduled data cleanup at 2 AM")


async def send_morning_brief(bot, session_maker):
    """Send morning brief to all users."""
    from datetime import datetime
    from bot.services.news import get_tech_news, format_news
    
    async with session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        news = await get_tech_news()
        
        for user in users:
            try:
                now = datetime.now()
                text = f"📊 <b>Good Morning! — {now.strftime('%A, %B %d')}</b>\n\n"
                
                # Weather per user
                has_custom_city = bool(user.city and user.city.strip())
                city_to_fetch = user.city if has_custom_city else settings.weather_city
                weather = await get_weather(city=city_to_fetch)
                weather_text = format_weather(weather)
                if not has_custom_city:
                    weather_text += "\n   <i>💡 Set your city with /setcity <city name> for personalized weather.</i>"
                
                text += weather_text + "\n\n"
                
                text += "📅 Check your calendar\n"
                text += "📝 Set your top 3 tasks\n"
                text += "💪 Complete your habits\n\n"
                
                # Tech News
                text += format_news(news) + "\n\n"
                
                text += "Have a productive day! ☀️"
                
                await bot.send_message(user.telegram_id, text)
            except Exception as e:
                logger.error(f"Failed to send brief to {user.telegram_id}: {e}")


async def send_evening_review(bot, session_maker):
    """Send evening review prompt to all users."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    async with session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        for user in users:
            try:
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{i}️⃣", callback_data=f"mood_{i}") for i in range(1, 11)]])
                
                await bot.send_message(
                    user.telegram_id,
                    "🌙 <b>Daily Review</b>\n\nHow was your day? (1-10)",
                    reply_markup=kb
                )
            except Exception as e:
                logger.error(f"Failed to send review to {user.telegram_id}: {e}")


async def fire_reminder(bot, user_id: int, message: str, reminder_id: int):
    """Fire a reminder to user."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Done", callback_data=f"reminder_ack:{reminder_id}")]
        ])
        
        await bot.send_message(
            user_id,
            f"⏰ <b>Reminder!</b>\n\n📝 {message}",
            reply_markup=kb
        )
    except Exception as e:
        logger.error(f"Failed to fire reminder {reminder_id}: {e}")


async def send_habit_reminder(bot, user_id: int, habit_id: int, habit_name: str):
    """Send habit reminder with Done/Skip buttons."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    try:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Done", callback_data=f"habit_done:{habit_id}"),
            InlineKeyboardButton(text="⏭ Skip", callback_data=f"habit_skip:{habit_id}"),
        ]])
        
        await bot.send_message(
            user_id,
            f"🎯 <b>Habit Reminder</b>\n\nDid you complete: <b>{habit_name}</b>?",
            reply_markup=kb
        )
    except Exception as e:
        logger.error(f"Failed to send habit reminder {habit_id}: {e}")


MAX_DB_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

async def cleanup_old_data(session_maker):
    """Clean up old data to keep DB under 100MB per user."""
    import os
    from datetime import timedelta
    
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    
    try:
        db_size = os.path.getsize(db_path)
        if db_size < MAX_DB_SIZE_BYTES:
            logger.info(f"DB size: {db_size / 1024 / 1024:.1f} MB — under limit")
            return
        
        logger.warning(f"DB size: {db_size / 1024 / 1024:.1f} MB — cleaning old data...")
        
        # Delete captures older than 90 days
        from sqlalchemy import delete
        from bot.database.models import Capture, Expense, HabitCompletion, Journal
        
        async with session_maker() as session:
            cutoff = datetime.now() - timedelta(days=90)
            
            await session.execute(
                delete(Capture).where(Capture.created_at < cutoff)
            )
            await session.execute(
                delete(HabitCompletion).where(HabitCompletion.completed_at < cutoff)
            )
            await session.execute(
                delete(Journal).where(Journal.created_at < cutoff)
            )
            
            # Keep expenses for 1 year
            expense_cutoff = datetime.now() - timedelta(days=365)
            await session.execute(
                delete(Expense).where(Expense.created_at < expense_cutoff)
            )
            
            await session.commit()
        
        # Vacuum SQLite
        async with session_maker() as session:
            await session.execute("VACUUM")
        
        new_size = os.path.getsize(db_path)
        logger.info(f"Cleanup done. DB size: {new_size / 1024 / 1024:.1f} MB")
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
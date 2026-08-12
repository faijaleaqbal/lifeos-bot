import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from bot.config import settings
from bot.database.init_db import init_db
from bot.database.crud import get_or_create_user
from bot.handlers import router as main_router
from bot.middlewares.db import DbSessionMiddleware
from bot.services.scheduler import setup_scheduler

# Setup loguru
logger.remove()
logger.add(
    settings.log_file,
    rotation="10 MB",
    retention="7 days",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)
logger.add(lambda msg: print(msg, end=""), level=settings.log_level)

@asynccontextmanager
async def lifespan(bot: Bot, dp: Dispatcher):
    # Startup
    logger.info("Starting LifeOS Bot...")
    await init_db()
    logger.info("Database initialized")
    
    # Setup scheduler
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    await setup_scheduler(scheduler, bot)
    scheduler.start()
    logger.info("Scheduler started")
    
    # Store scheduler in dp and bot for access in handlers
    dp["scheduler"] = scheduler
    bot["scheduler"] = scheduler
    
    # Register bot commands with Telegram (appears in menu)
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="🏠 Start bot & see welcome"),
        BotCommand(command="help", description="📖 Show all commands"),
        BotCommand(command="brief", description="🌅 Morning briefing"),
        BotCommand(command="spent", description="💰 Log expense"),
        BotCommand(command="report", description="📊 Expense report with chart"),
        BotCommand(command="habit", description="🎯 Manage habits"),
        BotCommand(command="done", description="✅ Mark habit complete"),
        BotCommand(command="habits", description="📅 Habit streak grid + chart"),
        BotCommand(command="remind", description="⏰ Set reminder"),
        BotCommand(command="reminders", description="📋 List active reminders"),
        BotCommand(command="cancel", description="❌ Cancel reminder by ID"),
        BotCommand(command="capture", description="📝 Save to Notion"),
        BotCommand(command="review", description="🌙 Evening review"),
        BotCommand(command="settings", description="⚙️ Configure integrations"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands registered")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    scheduler.shutdown()
    logger.info("Scheduler stopped")

async def main():
    # Bot & Dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.lifespan = lifespan
    
    # Middlewares
    dp.update.middleware(DbSessionMiddleware())
    
    # Routers
    dp.include_router(main_router)
    
    # Start polling
    logger.info("Bot starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
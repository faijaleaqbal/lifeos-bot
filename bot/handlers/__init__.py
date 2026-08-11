from aiogram import Router
from bot.handlers import commands, expenses, habits, reminders, capture, briefing, review

router = Router()
router.include_router(commands.router)
router.include_router(expenses.router)
router.include_router(habits.router)
router.include_router(reminders.router)
router.include_router(capture.router)
router.include_router(briefing.router)
router.include_router(review.router)
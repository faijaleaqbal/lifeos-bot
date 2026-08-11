from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from datetime import date, datetime, timedelta
from typing import List, Optional
from bot.database.models import User, Expense, Habit, HabitCompletion, Reminder, Journal, Capture

# User
async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

async def get_user(session: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

# Expenses
async def add_expense(session: AsyncSession, user_id: int, amount: int, category: str, description: str = "", expense_date: date = None) -> Expense:
    expense = Expense(
        user_id=user_id,
        amount=amount,
        category=category,
        description=description,
        date=expense_date or date.today()
    )
    session.add(expense)
    await session.commit()
    await session.refresh(expense)
    return expense

async def get_expenses_week(session: AsyncSession, user_id: int) -> List[Expense]:
    week_ago = date.today() - timedelta(days=7)
    result = await session.execute(
        select(Expense).where(
            and_(Expense.user_id == user_id, Expense.date >= week_ago)
        ).order_by(Expense.date.desc())
    )
    return result.scalars().all()

async def get_expenses_month(session: AsyncSession, user_id: int) -> List[Expense]:
    month_ago = date.today() - timedelta(days=30)
    result = await session.execute(
        select(Expense).where(
            and_(Expense.user_id == user_id, Expense.date >= month_ago)
        ).order_by(Expense.date.desc())
    )
    return result.scalars().all()

async def get_expense_summary_by_category(session: AsyncSession, user_id: int, days: int) -> dict:
    since = date.today() - timedelta(days=days)
    result = await session.execute(
        select(Expense.category, func.sum(Expense.amount))
        .where(and_(Expense.user_id == user_id, Expense.date >= since))
        .group_by(Expense.category)
    )
    return {row[0]: row[1] for row in result.all()}

# Habits
async def add_habit(session: AsyncSession, user_id: int, name: str, frequency: str, reminder_time: str = None) -> Habit:
    habit = Habit(user_id=user_id, name=name, frequency=frequency, reminder_time=reminder_time)
    session.add(habit)
    await session.commit()
    await session.refresh(habit)
    return habit

async def get_habits(session: AsyncSession, user_id: int, active_only: bool = True) -> List[Habit]:
    query = select(Habit).where(Habit.user_id == user_id)
    if active_only:
        query = query.where(Habit.active == True)
    result = await session.execute(query.order_by(Habit.created_at))
    return result.scalars().all()

async def get_habit(session: AsyncSession, habit_id: int) -> Optional[Habit]:
    result = await session.execute(select(Habit).where(Habit.id == habit_id))
    return result.scalar_one_or_none()

async def complete_habit(session: AsyncSession, habit_id: int, completion_date: date = None) -> HabitCompletion:
    completion = HabitCompletion(
        habit_id=habit_id,
        date=completion_date or date.today()
    )
    session.add(completion)
    
    # Update streak
    habit = await get_habit(session, habit_id)
    if habit:
        yesterday = date.today() - timedelta(days=1)
        result = await session.execute(
            select(HabitCompletion).where(
                and_(HabitCompletion.habit_id == habit_id, HabitCompletion.date == yesterday)
            )
        )
        completed_yesterday = result.scalar_one_or_none()
        
        if completed_yesterday:
            habit.streak_current += 1
        else:
            habit.streak_current = 1
        
        habit.streak_longest = max(habit.streak_longest, habit.streak_current)
    
    await session.commit()
    await session.refresh(completion)
    return completion

async def get_habit_completions(session: AsyncSession, habit_id: int, days: int = 365) -> List[date]:
    since = date.today() - timedelta(days=days)
    result = await session.execute(
        select(HabitCompletion.date)
        .where(and_(HabitCompletion.habit_id == habit_id, HabitCompletion.date >= since))
    )
    return [row[0] for row in result.all()]

# Reminders
async def add_reminder(session: AsyncSession, user_id: int, message: str, trigger_at: datetime, recurring_cron: str = None, job_id: str = None) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        message=message,
        trigger_at=trigger_at,
        recurring_cron=recurring_cron,
        job_id=job_id
    )
    session.add(reminder)
    await session.commit()
    await session.refresh(reminder)
    return reminder

async def get_active_reminders(session: AsyncSession, user_id: int) -> List[Reminder]:
    result = await session.execute(
        select(Reminder).where(
            and_(Reminder.user_id == user_id, Reminder.active == True)
        ).order_by(Reminder.trigger_at)
    )
    return result.scalars().all()

async def deactivate_reminder(session: AsyncSession, reminder_id: int) -> bool:
    result = await session.execute(select(Reminder).where(Reminder.id == reminder_id))
    reminder = result.scalar_one_or_none()
    if reminder:
        reminder.active = False
        await session.commit()
        return True
    return False

# Journal
async def add_journal_entry(session: AsyncSession, user_id: int, mood_score: int = None, win: str = "", improvement: str = "", notes: str = "", entry_date: date = None) -> Journal:
    entry = Journal(
        user_id=user_id,
        date=entry_date or date.today(),
        mood_score=mood_score,
        win=win,
        improvement=improvement,
        notes=notes
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry

async def get_journal_week(session: AsyncSession, user_id: int) -> List[Journal]:
    week_ago = date.today() - timedelta(days=7)
    result = await session.execute(
        select(Journal).where(
            and_(Journal.user_id == user_id, Journal.date >= week_ago)
        ).order_by(Journal.date.desc())
    )
    return result.scalars().all()

# Captures
async def add_capture(session: AsyncSession, user_id: int, content: str, notion_page_id: str = None, tags: list = None, source: str = "command") -> Capture:
    import json
    capture = Capture(
        user_id=user_id,
        notion_page_id=notion_page_id,
        content=content,
        tags=json.dumps(tags or []),
        source=source
    )
    session.add(capture)
    await session.commit()
    await session.refresh(capture)
    return capture
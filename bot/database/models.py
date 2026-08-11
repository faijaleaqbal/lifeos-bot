from sqlalchemy import (
    Column, Integer, BigInteger, Text, Date, DateTime, Boolean, 
    ForeignKey, UniqueConstraint, func
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(Text)
    timezone = Column(Text, default="Asia/Kolkata")
    notion_token = Column(Text)
    notion_db_id = Column(Text)
    google_sheets_id = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    expenses = relationship("Expense", back_populates="user")
    habits = relationship("Habit", back_populates="user")
    reminders = relationship("Reminder", back_populates="user")
    journal = relationship("Journal", back_populates="user")
    captures = relationship("Capture", back_populates="user")

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # paise
    category = Column(Text, nullable=False)
    description = Column(Text)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="expenses")

class Habit(Base):
    __tablename__ = "habits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(Text, nullable=False)
    frequency = Column(Text, nullable=False)  # daily, weekdays, custom cron
    reminder_time = Column(Text)  # HH:MM
    streak_current = Column(Integer, default=0)
    streak_longest = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="habits")
    completions = relationship("HabitCompletion", back_populates="habit")

class HabitCompletion(Base):
    __tablename__ = "habit_completions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    habit_id = Column(Integer, ForeignKey("habits.id"), nullable=False)
    date = Column(Date, nullable=False)
    completed_at = Column(DateTime, default=func.now())
    
    habit = relationship("Habit", back_populates="completions")
    
    __table_args__ = (UniqueConstraint("habit_id", "date", name="uq_habit_date"),)

class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    trigger_at = Column(DateTime, nullable=False, index=True)
    recurring_cron = Column(Text)  # None for one-time
    job_id = Column(Text, unique=True)  # APScheduler job ID
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="reminders")

class Journal(Base):
    __tablename__ = "journal"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    mood_score = Column(Integer)  # 1-10
    win = Column(Text)
    improvement = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="journal")
    
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_date"),)

class Capture(Base):
    __tablename__ = "captures"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notion_page_id = Column(Text)
    content = Column(Text, nullable=False)
    tags = Column(Text)  # JSON array
    source = Column(Text)  # forward, command, web
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="captures")
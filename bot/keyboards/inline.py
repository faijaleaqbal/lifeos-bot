from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Connect Notion", callback_data="setup_notion")
    builder.button(text="📊 Connect Google Sheets", callback_data="setup_sheets")
    builder.button(text="🌍 Set Timezone", callback_data="setup_timezone")
    builder.button(text="❌ Cancel", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()

def get_habit_done_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Done", callback_data=f"habit_done:{habit_id}")
    builder.button(text="⏭ Skip", callback_data=f"habit_skip:{habit_id}")
    builder.adjust(2)
    return builder.as_markup()

def get_reminder_cancel_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancel", callback_data=f"reminder_cancel:{reminder_id}")
    return builder.as_markup()

def get_report_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 This Week", callback_data="report_week")
    builder.button(text="📈 This Month", callback_data="report_month")
    builder.adjust(2)
    return builder.as_markup()

def get_habit_list_keyboard(habits: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for habit in habits:
        builder.button(text=f"{'🟢' if habit.active else '🔴'} {habit.name}", callback_data=f"habit_view:{habit.id}")
    builder.button(text="➕ Add Habit", callback_data="habit_add")
    builder.adjust(1)
    return builder.as_markup()

def get_reminder_list_keyboard(reminders: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rem in reminders:
        from datetime import datetime
        time_str = rem.trigger_at.strftime("%m/%d %H:%M")
        builder.button(text=f"🔔 {rem.message[:30]}... ({time_str})", callback_data=f"reminder_view:{rem.id}")
    builder.button(text="➕ Add Reminder", callback_data="reminder_add")
    builder.adjust(1)
    return builder.as_markup()
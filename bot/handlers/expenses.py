import re
from datetime import date
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.crud import get_or_create_user, add_expense, get_expense_summary_by_category, get_expenses_week, get_expenses_month

router = Router()

CATEGORIES = ["food", "transport", "shopping", "subscriptions", "bills", "other"]

@router.message(Command("spent"))
async def cmd_spent(message: Message, session, state: FSMContext):
    # Cancel any ongoing FSM
    await state.clear()
    
    user = await get_or_create_user(session, message.from_user.id)
    
    # Parse: /spent 120 coffee  OR  /spent 500 uber --cat transport
    args = message.text.replace("/spent", "", 1).strip()
    
    if not args:
        await message.answer(
            "💰 <b>Expense Tracker</b>\n\n"
            "Usage:\n"
            "<code>/spent 120 coffee</code> — logs ₹120 under 'food'\n"
            "<code>/spent 500 uber --cat transport</code> — logs ₹500 under 'transport'\n\n"
            "Categories: " + ", ".join(CATEGORIES)
        )
        return
    
    # Extract category with --cat flag
    category = "other"
    cat_match = re.search(r'--cat\s+(\w+)', args)
    if cat_match:
        category = cat_match.group(1).lower()
        args = re.sub(r'--cat\s+\w+', '', args).strip()
    
    if category not in CATEGORIES:
        await message.answer(f"❌ Invalid category. Use: {', '.join(CATEGORIES)}")
        return
    
    # Extract amount (first number)
    parts = args.split(None, 1)
    if not parts or not parts[0].isdigit():
        await message.answer("❌ Please provide amount first. Example: <code>/spent 120 coffee</code>")
        return
    
    amount = int(parts[0])
    description = parts[1] if len(parts) > 1 else ""
    
    # Store in paise
    expense = await add_expense(session, user.id, amount * 100, category, description)
    
    await message.answer(
        f"✅ <b>Expense logged!</b>\n"
        f"💰 ₹{amount} → <b>{category}</b>\n"
        f"📝 {description}\n"
        f"📅 {expense.date}\n\n"
        f"Use <code>/report week</code> to see summary."
    )

@router.message(Command("report"))
async def cmd_report(message: Message, session, state: FSMContext):
    await state.clear()
    
    user = await get_or_create_user(session, message.from_user.id)
    
    args = message.text.replace("/report", "", 1).strip().lower()
    
    if args == "month":
        expenses = await get_expenses_month(session, user.id)
        summary = await get_expense_summary_by_category(session, user.id, 30)
        period = "Last 30 days"
    else:
        expenses = await get_expenses_week(session, user.id)
        summary = await get_expense_summary_by_category(session, user.id, 7)
        period = "Last 7 days"
    
    if not expenses:
        await message.answer(f"📊 {period}: No expenses logged yet.\n\nUse <code>/spent 120 coffee</code> to log.")
        return
    
    total_paise = sum(e.amount for e in expenses)
    total = total_paise / 100
    
    text = f"📊 <b>Expense Report — {period}</b>\n\n"
    text += f"<b>Total: ₹{total:.2f}</b>\n"
    text += f"<b>Entries: {len(expenses)}</b>\n\n"
    text += "<b>By Category:</b>\n"
    
    for cat, amt_paise in sorted(summary.items(), key=lambda x: x[1], reverse=True):
        amt = amt_paise / 100
        pct = (amt_paise / total_paise * 100) if total_paise > 0 else 0
        text += f"  {cat}: ₹{amt:.2f} ({pct:.0f}%)\n"
    
    text += f"\n<b>Recent entries:</b>\n"
    for e in expenses[:5]:
        amt = e.amount / 100
        text += f"  • ₹{amt} {e.category} — {e.description or 'no desc'} ({e.date})\n"
    
    await message.answer(text)
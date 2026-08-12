"""Chart service — generate matplotlib charts for reports."""
import io
import logging
from datetime import date, timedelta
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Dark theme colors
BG_COLOR = '#0f172a'
TEXT_COLOR = '#f8fafc'
ACCENT_COLOR = '#6366f1'
GREEN = '#10b981'
ORANGE = '#f59e0b'
RED = '#ef4444'
CYAN = '#06b6d4'

CATEGORY_COLORS = {
    'food': '#10b981',
    'transport': '#06b6d4',
    'shopping': '#a855f7',
    'subscriptions': '#f59e0b',
    'bills': '#ef4444',
    'other': '#64748b',
}

async def generate_expense_chart(summary: dict, period: str = "week"):
    """
    Generate a pie chart of expenses by category.
    Returns BytesIO buffer (PNG image).
    """
    try:
        if not summary:
            return None
        
        categories = list(summary.keys())
        amounts = [summary[cat] / 100 for cat in categories]  # paise → rupees
        colors = [CATEGORY_COLORS.get(cat, '#64748b') for cat in categories]
        
        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        
        wedges, texts, autotexts = ax.pie(
            amounts,
            labels=categories,
            colors=colors,
            autopct=lambda pct: f"₹{pct/100*sum(amounts):.0f}\n({pct:.0f}%)",
            startangle=90,
            textprops={'color': TEXT_COLOR, 'fontsize': 10},
        )
        for autotext in autotexts:
            autotext.set_color(TEXT_COLOR)
            autotext.set_fontsize(9)
        
        total = sum(amounts)
        period_label = "Last 7 Days" if period == "week" else "Last 30 Days"
        ax.set_title(f"💰 Expenses — {period_label}\nTotal: ₹{total:.2f}", 
                     color=TEXT_COLOR, fontsize=14, fontweight='bold', pad=20)
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        return None

async def generate_habit_grid(completions_by_habit: dict, habit_names: list):
    """
    Generate GitHub-style contribution grid for habits.
    completions_by_habit: {habit_id: [list of dates]}
    """
    try:
        if not completions_by_habit:
            return None
        
        num_habits = len(completions_by_habit)
        today = date.today()
        days = 90  # Last 90 days
        
        fig, ax = plt.subplots(figsize=(12, max(3, num_habits * 1.5)))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        
        for i, (habit_id, dates) in enumerate(completions_by_habit.items()):
            for j in range(days):
                day = today - timedelta(days=days - j - 1)
                completed = day in dates
                color = GREEN if completed else '#1e293b'
                ax.scatter(j, i, color=color, s=100, marker='s')
        
        ax.set_yticks(range(num_habits))
        ax.set_yticklabels(habit_names[:num_habits], color=TEXT_COLOR, fontsize=10)
        ax.set_xlabel("Days ago →", color=TEXT_COLOR)
        ax.set_title("🎯 Habit Streaks (Last 90 Days)", 
                     color=TEXT_COLOR, fontsize=14, fontweight='bold')
        
        ax.tick_params(colors=TEXT_COLOR)
        for spine in ax.spines.values():
            spine.set_color(TEXT_COLOR)
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Habit grid generation failed: {e}")
        return None

async def generate_mood_chart(mood_entries: list):
    """
    Generate mood trend line chart.
    mood_entries: list of (date, mood_score) tuples
    """
    try:
        if not mood_entries:
            return None
        
        dates = [entry[0] for entry in mood_entries]
        scores = [entry[1] for entry in mood_entries if entry[1] is not None]
        
        if not scores:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        
        ax.fill_between(range(len(scores)), scores, alpha=0.3, color=ACCENT_COLOR)
        ax.plot(range(len(scores)), scores, color=ACCENT_COLOR, linewidth=2, marker='o')
        
        ax.set_ylim(0, 10)
        ax.set_yticks(range(0, 11))
        ax.set_title("🌙 Mood Trend", color=TEXT_COLOR, fontsize=14, fontweight='bold')
        ax.set_ylabel("Mood (1-10)", color=TEXT_COLOR)
        ax.tick_params(colors=TEXT_COLOR)
        
        for spine in ax.spines.values():
            spine.set_color(TEXT_COLOR)
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Mood chart failed: {e}")
        return None
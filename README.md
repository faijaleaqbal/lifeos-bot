# LifeOS Bot - Personal Telegram Assistant

A personal daily operating system bot for Telegram with:
- Morning briefings (weather, calendar, tasks, news)
- Expense tracking with Google Sheets sync
- Habit tracking with streaks and reminders
- Smart reminders with natural language parsing
- Quick capture to Notion
- Daily evening review

## Quick Start

```bash
# 1. Clone & setup
git clone <your-repo> lifeos-bot
cd lifeos-bot

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env with your tokens

# 5. Initialize database
python -m bot.database.init_db

# 6. Run
python -m bot.main
```

## Required Setup

### 1. Telegram Bot Token
- Message `@BotFather` → `/newbot`
- Name: `LifeOS` (or your choice)
- Username: `yourlifeos_bot` (must end in `_bot`)
- Copy token → add to `.env` as `BOT_TOKEN`

### 2. Admin ID
- Message `@userinfobot` → get your Telegram user ID
- Add to `.env` as `ADMIN_ID`

### 3. Google Sheets (for expenses)
- Google Cloud Console → Create Service Account
- Enable Google Sheets API
- Download JSON credentials → save as `credentials/google_sheets.json`
- Create a Google Sheet with columns: `Date, Amount, Category, Description`
- Share sheet with service account email (from JSON)
- Copy Sheet ID from URL → add to `.env` as `GOOGLE_SHEETS_ID`

### 4. Notion (for quick capture)
- Go to https://www.notion.so/my-integrations
- Create new integration → Copy `Internal Integration Token`
- Create a database with properties: Title, Content, Tags, Date, Source
- Share database with integration
- Copy Database ID from URL → add to `.env` as `NOTION_DATABASE_ID`
- Add token to `.env` as `NOTION_TOKEN`

### 5. OpenWeatherMap (for weather)
- Sign up at https://openweathermap.org/api
- Get free API key (1000 calls/day)
- Add to `.env` as `OPENWEATHER_API_KEY`

### 6. Google Calendar (optional, for briefing)
- Google Cloud Console → Enable Calendar API
- Create OAuth2 credentials
- Add to `.env` as `GOOGLE_CALENDAR_CREDENTIALS_FILE`

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome + setup status |
| `/help` | Command reference |
| `/brief` | Manual morning briefing |
| `/spent 120 coffee` | Log expense (amount in ₹) |
| `/report week` | Expense report + chart |
| `/habit add "Run" --time 06:30` | Create habit |
| `/done "Run"` | Mark habit complete |
| `/habits` | Visual streak grid |
| `/remind 10m "Call mom"` | Set reminder |
| `/reminders` | List active reminders |
| `/capture "Idea"` | Save to Notion |
| `/review` | Daily evening review |
| `/settings` | Configure integrations |

## Natural Language Reminders

```
/remind 10m "Take a break"
/remind 2h "Meeting prep"
/remind tomorrow 9am "Team standup"
/remind monday 10am "Weekly review"
/remind every friday 5pm "Weekly report"
```

## Deployment

### Docker
```bash
docker compose up -d
```

### Systemd (VPS)
```bash
sudo cp lifeos-bot.service /etc/systemd/system/
sudo systemctl enable lifeos-bot
sudo systemctl start lifeos-bot
```

See `docker-compose.yml` and `lifeos-bot.service` for details.

## Project Structure
```
lifeos-bot/
├── bot/
│   ├── main.py                 # Entry point
│   ├── config.py               # Settings (pydantic)
│   ├── database/
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── crud.py             # Database operations
│   │   └── init_db.py          # Table creation
│   ├── handlers/
│   │   ├── commands.py         # /start, /help, /settings
│   │   ├── expenses.py         # /spent, /report
│   │   ├── habits.py           # /habit, /done, /habits
│   │   ├── reminders.py        # /remind, /reminders
│   │   ├── capture.py          # /capture, forwards
│   │   ├── briefing.py         # /brief, scheduled
│   │   └── review.py           # /review, evening
│   ├── services/
│   │   ├── weather.py          # OpenWeatherMap
│   │   ├── calendar.py         # Google Calendar
│   │   ├── sheets.py           # Google Sheets
│   │   ├── notion.py           # Notion API
│   │   ├── charts.py           # Matplotlib charts
│   │   └── scheduler.py        # APScheduler setup
│   ├── middlewares/
│   │   └── db.py               # DB session middleware
│   ├── keyboards/
│   │   └── inline.py           # Inline keyboards
│   └── utils/
│       ├── parsing.py          # Natural language parsing
│       └── formatting.py       # Message formatting
├── credentials/                # API credentials (gitignored)
├── data/                       # SQLite DB (gitignored)
├── logs/                       # Log files (gitignored)
├── tests/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## Development

### Run Tests
```bash
pytest tests/ -v
```

### Code Style
```bash
# Type checking
pip install pyright
pyright bot/

# Linting
pip install ruff
ruff check bot/
```

## License
MIT - Feel free to use for your own personal bot!
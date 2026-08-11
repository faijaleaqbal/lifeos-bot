from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    # Bot
    bot_token: str = Field(..., validation_alias="BOT_TOKEN")
    admin_id: int = Field(..., validation_alias="ADMIN_ID")
    
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///data/lifeos.db", validation_alias="DATABASE_URL")
    
    # Timezone
    timezone: str = Field(default="Asia/Kolkata", validation_alias="TIMEZONE")
    
    # Google Sheets
    google_sheets_credentials_file: Path = Field(default=Path("credentials/google_sheets.json"), validation_alias="GOOGLE_SHEETS_CREDENTIALS_FILE")
    google_sheets_id: str = Field(default="", validation_alias="GOOGLE_SHEETS_ID")
    
    # Notion
    notion_token: str = Field(default="", validation_alias="NOTION_TOKEN")
    notion_database_id: str = Field(default="", validation_alias="NOTION_DATABASE_ID")
    
    # OpenWeatherMap
    openweather_api_key: str = Field(default="", validation_alias="OPENWEATHER_API_KEY")
    weather_city: str = Field(default="Malda,IN", validation_alias="WEATHER_CITY")
    
    # Google Calendar
    google_calendar_credentials_file: Path = Field(default=Path("credentials/google_calendar.json"), validation_alias="GOOGLE_CALENDAR_CREDENTIALS_FILE")
    google_calendar_token_file: Path = Field(default=Path("credentials/calendar_token.json"), validation_alias="GOOGLE_CALENDAR_TOKEN_FILE")
    
    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_file: Path = Field(default=Path("logs/bot.log"), validation_alias="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()
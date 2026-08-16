"""Google Sheets service — async append rows for expense tracking."""
import asyncio
import logging
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from bot.config import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_service_account_email() -> str:
    """Get the client_email from the service account credentials file."""
    try:
        creds_file = settings.google_sheets_credentials_file
        if creds_file.exists():
            import json
            with open(creds_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('client_email', '')
    except Exception as e:
        logger.error(f"Failed to read service account email: {e}")
    return ''

def _get_service():
    """Create Google Sheets service (sync — called in thread executor)."""
    creds = Credentials.from_service_account_file(
        str(settings.google_sheets_credentials_file),
        scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=creds)

def _append_row_sync(sheet_id: str, values: list):
    """Append a single row to the sheet (sync)."""
    service = _get_service()
    body = {
        'values': [values]
    }
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range='A:D',
        valueInputOption='RAW',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()
    return result

async def append_expense_row(sheet_id: str, amount: int, category: str, description: str, date_str: str):
    """
    Append an expense row to Google Sheets asynchronously.
    amount is in paise — converted to rupees for display.
    """
    try:
        rupees = amount / 100
        values = [date_str, f"₹{rupees:.2f}", category, description]
        
        # Run sync Google API call in thread executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _append_row_sync, sheet_id, values)
        logger.info(f"Appended to Google Sheets: {values}")
        return True
    except Exception as e:
        logger.error(f"Google Sheets append failed: {e}")
        return False

def _check_sheet_exists_sync(sheet_id: str):
    """Check if sheet is accessible."""
    try:
        service = _get_service()
        result = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        return result.get('properties', {}).get('title', 'Unknown')
    except Exception:
        return None

async def check_sheet_access(sheet_id: str):
    """Check if Google Sheet is accessible. Returns sheet title or None."""
    try:
        loop = asyncio.get_event_loop()
        title = await loop.run_in_executor(None, _check_sheet_exists_sync, sheet_id)
        return title
    except Exception as e:
        logger.error(f"Sheet check failed: {e}")
        return None
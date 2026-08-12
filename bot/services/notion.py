"""Notion service — create pages in Notion database for quick capture."""
import asyncio
import logging
from notion_client import Client
from bot.config import settings

logger = logging.getLogger(__name__)

def _get_client(token: str):
    """Create Notion client with user's token."""
    return Client(auth=token)

def _create_page_sync(token: str, database_id: str, title: str, content: str = "", tags: list = None):
    """Create a page in Notion database (sync)."""
    client = _get_client(token)
    
    properties = {
        "Name": {
            "title": [{"text": {"content": title[:2000]}}]
        },
    }
    
    # Try adding tags as multi-select if property exists
    if tags:
        try:
            properties["Tags"] = {
                "multi_select": [{"name": tag} for tag in tags[:10]]
            }
        except Exception:
            pass
    
    # Add content as a paragraph in the page body
    children = []
    if content:
        # Split content into chunks of 2000 chars (Notion limit)
        for i in range(0, len(content), 2000):
            chunk = content[i:i+2000]
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            })
    
    page = client.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        children=children if children else None
    )
    return page

async def create_notion_page(token: str, database_id: str, title: str, content: str = "", tags: list = None):
    """
    Create a page in Notion asynchronously.
    Returns page URL or None on failure.
    """
    try:
        loop = asyncio.get_event_loop()
        page = await loop.run_in_executor(
            None, _create_page_sync, token, database_id, title, content, tags
        )
        page_url = page.get('url', '')
        logger.info(f"Created Notion page: {page_url}")
        return page_url
    except Exception as e:
        logger.error(f"Notion page creation failed: {e}")
        return None

def _search_pages_sync(token: str, query: str):
    """Search pages in Notion (sync)."""
    client = _get_client(token)
    results = client.databases.query(
        database_id=settings.notion_database_id,
        filter={
            "property": "Name",
            "title": {"contains": query}
        }
    )
    return results.get('results', [])

async def search_notion(token: str, database_id: str, query: str):
    """Search Notion pages asynchronously. Returns list of (title, url)."""
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _search_pages_sync, token, query)
        
        pages = []
        for page in results[:5]:
            title_prop = page.get('properties', {}).get('Name', {})
            title_items = title_prop.get('title', [])
            title = title_items[0]['text']['content'] if title_items else 'Untitled'
            url = page.get('url', '')
            pages.append((title, url))
        
        return pages
    except Exception as e:
        logger.error(f"Notion search failed: {e}")
        return []
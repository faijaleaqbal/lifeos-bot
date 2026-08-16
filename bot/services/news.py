"""Tech news service — fetch headlines from NewsAPI.org."""
import html
import logging
import httpx
from bot.config import settings

logger = logging.getLogger(__name__)

async def get_tech_news(api_key: str = None, page_size: int = 3) -> dict | None:
    """
    Fetch top tech news headlines from NewsAPI.org.
    Returns dict: {"articles": [{"title": ..., "source": {"name": ...}, "url": ...}]} or {"error": msg}
    """
    api_key = settings.news_api_key if api_key is None else api_key
    
    if not api_key:
        return {"error": "API key not configured"}
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "category": "technology",
                    "language": "en",
                    "pageSize": page_size,
                    "apiKey": api_key,
                },
                timeout=10
            )
            if response.status_code == 401:
                logger.error("NewsAPI authentication failed (401)")
                return {"error": "Invalid API key"}
            elif response.status_code == 429:
                logger.error("NewsAPI rate limit exceeded (429)")
                return {"error": "Rate limit exceeded"}
                
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "ok":
                error_msg = data.get("message", "API returned non-ok status")
                logger.error(f"NewsAPI error: {error_msg}")
                return {"error": error_msg}
                
            return {
                "articles": data.get("articles", [])
            }
    except httpx.TimeoutException:
        logger.error("News fetch timed out")
        return {"error": "Request timed out"}
    except Exception as e:
        logger.error(f"News fetch failed: {e}")
        return {"error": "Unable to fetch news"}

import re

def format_news(news_data: dict) -> str:
    """Format tech news dict into Telegram message matching brief style."""
    if not news_data:
        return "📰 <b>Tech News:</b>\n   Add NEWS_API_KEY in .env for live news"
        
    if "error" in news_data:
        return f"📰 <b>Tech News:</b>\n   News unavailable ({html.escape(news_data['error'])})"
        
    articles = news_data.get("articles", [])
    if not articles:
        return "📰 <b>Tech News:</b>\n   No tech headlines currently available."
        
    lines = ["📰 <b>Tech News:</b>"]
    for article in articles[:3]:
        title = (article.get("title") or "").strip()
        source = (article.get("source") or {}).get("name", "").strip()
        
        if not title:
            continue
            
        # Strip duplicate source from end of title if present (e.g., "Title - Source" or "Title - Source news")
        if source:
            cleaned_title = re.sub(r'\s*-\s*' + re.escape(source) + r'.*$', '', title, flags=re.IGNORECASE).strip()
            if cleaned_title:
                title = cleaned_title
            
        if source:
            lines.append(f"   • {html.escape(title)} (<i>{html.escape(source)}</i>)")
        else:
            lines.append(f"   • {html.escape(title)}")
            
    return "\n".join(lines)

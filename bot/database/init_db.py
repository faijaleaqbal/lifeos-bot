from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from bot.config import settings
from bot.database.models import Base

async def init_db():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Ensure 'city' column exists on existing databases
        result = await conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        if "city" not in columns:
            await conn.execute(text("ALTER TABLE users ADD COLUMN city TEXT"))
            
    await engine.dispose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
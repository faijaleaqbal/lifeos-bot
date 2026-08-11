from sqlalchemy.ext.asyncio import create_async_engine
from bot.config import settings
from bot.database.models import Base

async def init_db():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
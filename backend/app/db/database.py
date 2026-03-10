from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.models.models import Base
import asyncio
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    for attempt in range(10):
        try:
            async with engine.begin() as conn:
                # Drop all and recreate — safe on fresh deploy
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
            return
        except Exception as e:
            logger.warning(f"DB init attempt {attempt+1}/10 failed: {e}")
            await asyncio.sleep(3)
    raise Exception("Could not connect to database after 10 attempts")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

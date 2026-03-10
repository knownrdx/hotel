from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_sync_for_hotel(hotel_id: int):
    from app.db.database import AsyncSessionLocal
    from app.models.models import Hotel
    from app.services.sync_engine import SyncEngine

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Hotel).where(Hotel.id == hotel_id))
        hotel = result.scalar_one_or_none()
        if hotel:
            engine = SyncEngine(db)
            result = await engine.sync_hotel(hotel)
            logger.info(f"Scheduled sync for hotel {hotel.name}: {result}")


async def run_all_syncs():
    from app.db.database import AsyncSessionLocal
    from app.models.models import Hotel
    from app.services.sync_engine import SyncEngine

    async with AsyncSessionLocal() as db:
        engine = SyncEngine(db)
        await engine.sync_all_hotels()


def start_scheduler():
    # Run global sync every 5 minutes
    scheduler.add_job(
        run_all_syncs,
        trigger=IntervalTrigger(minutes=5),
        id="global_sync",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown()

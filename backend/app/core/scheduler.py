from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_all_syncs():
    from app.services.sync_engine import sync_engine
    try:
        await sync_engine.sync_all_hotels()
    except Exception as e:
        logger.error(f"Scheduler sync error: {e}", exc_info=True)


def start_scheduler():
    scheduler.add_job(run_all_syncs, IntervalTrigger(minutes=5), id="sync_all", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown(wait=False)

"""Hourly scheduler for the data retention worker (warn expiry, log scrubbing)."""

import asyncio

from core.config import settings
from core.database import async_session_factory
from core.logger import logger
from services.cleaner.retention import DataRetentionWorker

RETENTION_INTERVAL_SECONDS = 60 * 60


async def run_retention_loop() -> None:
    """Background loop: expire warns and archive old logs once per hour."""
    logger.info("Data retention scheduler started.")
    while True:
        await asyncio.sleep(RETENTION_INTERVAL_SECONDS)
        try:
            async with async_session_factory() as session:
                await DataRetentionWorker.expire_old_warns(session)
                _, records = await DataRetentionWorker.purge_and_archive_logs(
                    session,
                    retention_days=settings.LOGS_RETENTION_DAYS,
                )
                await session.commit()
                # Persist the archive only after the commit: a rollback must
                # never leave rows alive that were already archived
                DataRetentionWorker.write_archive(records)
        except asyncio.CancelledError:
            raise
        except Exception as loop_err:
            logger.error(f"Retention loop error: {loop_err}")

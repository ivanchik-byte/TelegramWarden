"""Data retention worker: warning expirations, log compression, and DB archiving."""

import gzip
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from core.logger import logger
from models import AuditLog, Warn

ARCHIVE_DIR = Path("logs/archives")
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


class DataRetentionWorker:
    """Performs scheduled cleanup and archival of database records."""

    @classmethod
    async def expire_old_warns(cls, session: AsyncSession) -> int:
        """Deactivate warnings that have passed their expiration date."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Warn)
            .where(Warn.is_active == True, Warn.expires_at <= now)  # noqa: E712
            .values(is_active=False)
        )
        result = await session.execute(stmt)
        expired_count = result.rowcount
        if expired_count > 0:
            logger.info(f"Deactivated {expired_count} expired warnings.")
        return expired_count

    @classmethod
    async def purge_and_archive_logs(cls, session: AsyncSession, retention_days: int = 30) -> tuple[int, list[dict]]:
        """Scrub raw message snippets older than the retention period.

        Returns the archived records for the caller to persist AFTER the DB
        transaction commits — writing the archive before the commit meant a
        rollback would leave rows alive and get them archived again.
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # Query old logs that still retain raw message text
        stmt = select(AuditLog).where(
            AuditLog.created_at <= cutoff_date,
            AuditLog.raw_message_snippet.isnot(None),
        )
        result = await session.execute(stmt)
        old_logs = result.scalars().all()

        if not old_logs:
            return 0, []

        # Build archive payload
        archive_records = []
        for log in old_logs:
            archive_records.append({
                "id": log.id,
                "chat_id": log.chat_id,
                "user_id": log.user_id,
                "action_type": log.action_type,
                "category": log.category,
                "reason": log.reason,
                "confidence": log.confidence,
                "raw_message_snippet": log.raw_message_snippet,
                "created_at": log.created_at.isoformat(),
                "is_false_positive": log.is_false_positive,
            })

        try:
            # Scrub raw text from database to reclaim storage (committed by caller)
            for log in old_logs:
                log.raw_message_snippet = None
                log.evidence_file_id = None

            await session.flush()
            return len(archive_records), archive_records

        except Exception as err:
            logger.error(f"Failed to prepare audit log archival: {err}")
            return 0, []

    @classmethod
    def write_archive(cls, archive_records: list[dict]) -> bool:
        """Append scrubbed records to the compressed archive file."""
        if not archive_records:
            return True

        now = datetime.now(timezone.utc)
        archive_path = ARCHIVE_DIR / f"audit_archive_{now.year}_{now.month:02d}.json.gz"
        try:
            with gzip.open(archive_path, "at", encoding="utf-8") as gz_file:
                for rec in archive_records:
                    gz_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
            logger.info(f"Archived {len(archive_records)} audit logs into {archive_path}")
            return True
        except Exception as err:
            logger.error(f"Failed to write audit archive: {err}")
            return False

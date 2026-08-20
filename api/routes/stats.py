"""API routes for moderation statistics and audit log views."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import TelegramUser, get_current_telegram_user
from api.schemas import AuditLogItemSchema, CategoryStatItem, ChatStatsResponseSchema
from core.config import settings
from core.database import get_db_session
from models import AuditLog, Chat, Warn

router = APIRouter(prefix="/stats", tags=["Stats"])


async def _verify_chat_access(chat_id: int, user_id: int, session: AsyncSession) -> None:
    """Verify that user is superadmin or in chat's whitelist."""
    if user_id in settings.superadmin_id_list:
        return
    res = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res.scalar_one_or_none()
    if not chat_db or user_id not in (chat_db.whitelisted_users or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to view stats for this chat",
        )


@router.get("/{chat_id}", response_model=ChatStatsResponseSchema)
async def get_chat_statistics(
    chat_id: int,
    user: TelegramUser = Depends(get_current_telegram_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatStatsResponseSchema:
    """Get aggregated moderation metrics and category breakdown."""
    await _verify_chat_access(chat_id, user.id, session)

    # 1. Total violations count
    total_viol_res = await session.execute(
        select(func.count(AuditLog.id)).where(AuditLog.chat_id == chat_id)
    )
    total_violations = total_viol_res.scalar() or 0

    # 2. Total warns issued
    total_warns_res = await session.execute(
        select(func.count(Warn.id)).where(Warn.chat_id == chat_id)
    )
    total_warns = total_warns_res.scalar() or 0

    # 3. Bans count
    bans_res = await session.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.chat_id == chat_id, AuditLog.action_type == "ban_user"
        )
    )
    total_bans = bans_res.scalar() or 0

    # 4. Mutes count
    mutes_res = await session.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.chat_id == chat_id, AuditLog.action_type == "mute_user"
        )
    )
    total_mutes = mutes_res.scalar() or 0

    # 5. False positives count
    fp_res = await session.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.chat_id == chat_id, AuditLog.is_false_positive == True  # noqa: E712
        )
    )
    false_positives = fp_res.scalar() or 0

    # 6. Violations by category
    cat_res = await session.execute(
        select(AuditLog.category, func.count(AuditLog.id))
        .where(AuditLog.chat_id == chat_id)
        .group_by(AuditLog.category)
    )
    categories = [
        CategoryStatItem(category=row[0], count=row[1]) for row in cat_res.all()
    ]

    return ChatStatsResponseSchema(
        chat_id=chat_id,
        total_violations=total_violations,
        total_warns_issued=total_warns,
        total_bans=total_bans,
        total_mutes=total_mutes,
        false_positives_count=false_positives,
        violations_by_category=categories,
    )


@router.get("/{chat_id}/logs", response_model=list[AuditLogItemSchema])
async def get_recent_audit_logs(
    chat_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: TelegramUser = Depends(get_current_telegram_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuditLogItemSchema]:
    """Get paginated recent moderation events."""
    await _verify_chat_access(chat_id, user.id, session)

    stmt = (
        select(AuditLog)
        .where(AuditLog.chat_id == chat_id)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    logs = result.scalars().all()

    return [
        AuditLogItemSchema(
            id=log.id,
            user_id=log.user_id,
            action_type=log.action_type,
            category=log.category,
            reason=log.reason,
            confidence=log.confidence,
            raw_message_snippet=log.raw_message_snippet,
            created_at=log.created_at,
            is_false_positive=log.is_false_positive,
        )
        for log in logs
    ]

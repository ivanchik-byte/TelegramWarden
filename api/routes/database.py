"""API routes for interactive Database Visualizer & Explorer."""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import TelegramUser, get_current_telegram_user
from core.config import settings
from core.database import get_db_session
from models import AuditLog, Chat, User, Warn

router = APIRouter(prefix="/database", tags=["Database Explorer"])


def _check_superadmin(user: TelegramUser) -> None:
    """Verify that user is a configured superadmin."""
    if user.id not in settings.superadmin_id_list:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Database explorer is restricted to SuperAdmins",
        )


@router.get("/tables")
async def list_database_tables(
    user: TelegramUser = Depends(get_current_telegram_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List all database tables with total row counts and column schemas."""
    _check_superadmin(user)

    tables_info = [
        {
            "id": "chats",
            "name": "chats",
            "title": "Группы (chats)",
            "description": "Конфигурация сообществ, фильтры, капча и ночной режим",
            "model": Chat,
            "columns": [
                {"key": "chat_id", "label": "ID Чата", "type": "bigint", "is_pk": True},
                {"key": "title", "label": "Название", "type": "string"},
                {"key": "is_active", "label": "Защита", "type": "bool"},
                {"key": "ai_moderation_enabled", "label": "ИИ", "type": "bool"},
                {"key": "ai_confidence_threshold", "label": "Порог %", "type": "float"},
                {"key": "captcha_enabled", "label": "Капча", "type": "bool"},
                {"key": "warn_limit", "label": "Варны", "type": "int"},
                {"key": "warn_punishment", "label": "Санкция", "type": "string"},
                {"key": "night_mode_enabled", "label": "Ночь", "type": "bool"},
                {"key": "created_at", "label": "Создан", "type": "datetime"},
            ],
        },
        {
            "id": "users",
            "name": "users",
            "title": "Пользователи (users)",
            "description": "Профили участников, уровень доверия и статистика нарушений",
            "model": User,
            "columns": [
                {"key": "id", "label": "ID", "type": "int", "is_pk": True},
                {"key": "telegram_id", "label": "Telegram ID", "type": "bigint"},
                {"key": "chat_id", "label": "ID Чата", "type": "bigint"},
                {"key": "username", "label": "Username", "type": "string"},
                {"key": "first_name", "label": "Имя", "type": "string"},
                {"key": "trust_score", "label": "Траст", "type": "float"},
                {"key": "violations_count", "label": "Нарушений", "type": "int"},
                {"key": "is_banned", "label": "Бан", "type": "bool"},
                {"key": "first_seen", "label": "Первый вход", "type": "datetime"},
            ],
        },
        {
            "id": "warns",
            "name": "warns",
            "title": "Предупреждения (warns)",
            "description": "Активные и истекшие варны участников",
            "model": Warn,
            "columns": [
                {"key": "id", "label": "ID", "type": "int", "is_pk": True},
                {"key": "user_id", "label": "ID Пользователя", "type": "int"},
                {"key": "chat_id", "label": "ID Чата", "type": "bigint"},
                {"key": "reason", "label": "Причина", "type": "string"},
                {"key": "admin_telegram_id", "label": "Админ ID", "type": "bigint"},
                {"key": "is_active", "label": "Активен", "type": "bool"},
                {"key": "created_at", "label": "Выдан", "type": "datetime"},
            ],
        },
        {
            "id": "audit_logs",
            "name": "audit_logs",
            "title": "Журнал аудита (audit_logs)",
            "description": "События безопасности, срабатывания ИИ и модерации",
            "model": AuditLog,
            "columns": [
                {"key": "id", "label": "ID", "type": "int", "is_pk": True},
                {"key": "chat_id", "label": "ID Чата", "type": "bigint"},
                {"key": "user_id", "label": "ID Юзера", "type": "int"},
                {"key": "action_type", "label": "Действие", "type": "string"},
                {"key": "category", "label": "Категория", "type": "string"},
                {"key": "confidence", "label": "ИИ Уверенность %", "type": "float"},
                {"key": "reason", "label": "Причина", "type": "string"},
                {"key": "is_false_positive", "label": "False+", "type": "bool"},
                {"key": "created_at", "label": "Время", "type": "datetime"},
            ],
        },
    ]

    result = []
    for t in tables_info:
        model = t["model"]
        cnt_res = await session.execute(select(func.count()).select_from(model))
        total_count = cnt_res.scalar() or 0
        result.append({
            "id": t["id"],
            "name": t["name"],
            "title": t["title"],
            "description": t["description"],
            "total_rows": total_count,
            "columns": t["columns"],
        })

    return result


@router.get("/records")
async def get_table_records(
    table: str = Query(..., description="Table name: chats, users, warns, audit_logs"),
    limit: int = Query(default=30, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    user: TelegramUser = Depends(get_current_telegram_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve records from specified database table with pagination."""
    _check_superadmin(user)

    table_map = {
        "chats": Chat,
        "users": User,
        "warns": Warn,
        "audit_logs": AuditLog,
    }

    if table not in table_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid table name '{table}'. Available: {list(table_map.keys())}",
        )

    model = table_map[table]
    query = select(model)

    # Optional search filtering
    if search:
        search_term = f"%{search.strip()}%"
        if table == "chats":
            query = query.where(Chat.title.ilike(search_term))
        elif table == "users":
            query = query.where(User.first_name.ilike(search_term) | User.username.ilike(search_term))
        elif table == "warns":
            query = query.where(Warn.reason.ilike(search_term))
        elif table == "audit_logs":
            query = query.where(AuditLog.reason.ilike(search_term) | AuditLog.category.ilike(search_term))

    # Get total count
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await session.execute(count_stmt)
    total_count = total_res.scalar() or 0

    # Order by primary key / timestamp desc
    if hasattr(model, "created_at"):
        query = query.order_by(model.created_at.desc())
    elif hasattr(model, "id"):
        query = query.order_by(model.id.desc())

    query = query.limit(limit).offset(offset)
    records_res = await session.execute(query)
    rows = records_res.scalars().all()

    # Convert ORM instances to JSON-friendly dicts
    serialized = []
    for r in rows:
        row_dict = {}
        for col in r.__table__.columns:
            val = getattr(r, col.name)
            if hasattr(val, "isoformat"):
                row_dict[col.name] = val.isoformat()
            else:
                row_dict[col.name] = val
        serialized.append(row_dict)

    return {
        "table": table,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "records": serialized,
    }

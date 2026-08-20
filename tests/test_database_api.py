"""Unit & Integration tests for Database Explorer API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import TelegramUser, get_current_telegram_user
from api.main import app
from core.database import get_db_session
from models import AuditLog, Chat, User, Warn


@pytest.mark.asyncio
async def test_database_tables_metadata(db_session: AsyncSession):
    """Verify that /api/database/tables returns schema and counts for superadmin."""
    chat = Chat(chat_id=-100999001, title="DB Test Chat")
    user = User(chat_id=-100999001, telegram_id=555444, first_name="DB Tester")
    db_session.add_all([chat, user])
    await db_session.commit()

    app.dependency_overrides[get_db_session] = lambda: db_session
    # Superadmin ID 8667615215
    app.dependency_overrides[get_current_telegram_user] = lambda: TelegramUser(id=8667615215, first_name="Owner")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/database/tables")
        assert res.status_code == 200
        tables = res.json()
        assert len(tables) == 4
        table_ids = [t["id"] for t in tables]
        assert "chats" in table_ids
        assert "users" in table_ids
        assert "warns" in table_ids
        assert "audit_logs" in table_ids

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_database_records_pagination_and_search(db_session: AsyncSession):
    """Verify that /api/database/records supports table filtering and search."""
    chat1 = Chat(chat_id=-100999002, title="Alpha Group")
    chat2 = Chat(chat_id=-100999003, title="Beta Group")
    db_session.add_all([chat1, chat2])
    await db_session.commit()

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_telegram_user] = lambda: TelegramUser(id=8667615215, first_name="Owner")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch all chats
        res_all = await client.get("/api/database/records?table=chats&limit=10")
        assert res_all.status_code == 200
        data_all = res_all.json()
        assert data_all["total"] >= 2
        assert len(data_all["records"]) >= 2

        # 2. Search filtering
        res_search = await client.get("/api/database/records?table=chats&search=Alpha")
        assert res_search.status_code == 200
        data_search = res_search.json()
        assert len(data_search["records"]) == 1
        assert data_search["records"][0]["title"] == "Alpha Group"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_database_explorer_forbidden_for_regular_users(db_session: AsyncSession):
    """Verify that non-superadmins receive 403 Forbidden on database explorer."""
    app.dependency_overrides[get_db_session] = lambda: db_session
    # Regular user ID not in superadmin list
    app.dependency_overrides[get_current_telegram_user] = lambda: TelegramUser(id=111222333, first_name="Stranger")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res1 = await client.get("/api/database/tables")
        assert res1.status_code == 403

        res2 = await client.get("/api/database/records?table=chats")
        assert res2.status_code == 403

    app.dependency_overrides.clear()

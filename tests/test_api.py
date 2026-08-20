"""Integration and unit tests for FastAPI Mini App endpoints and auth."""

import hashlib
import hmac
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import validate_telegram_init_data, get_current_telegram_user, TelegramUser
from api.main import app
from core.database import get_db_session
from models import Chat, AuditLog, User


def generate_valid_init_data(user_id: int, bot_token: str) -> str:
    """Helper generating valid HMAC-SHA256 signed Telegram initData string."""
    params = {
        "auth_date": "1700000000",
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": f'{{"id":{user_id},"first_name":"Admin","username":"admin_user"}}',
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hash_sig = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    
    import urllib.parse
    params_with_hash = dict(params)
    params_with_hash["hash"] = hash_sig
    return urllib.parse.urlencode(params_with_hash)


def test_telegram_init_data_validation():
    """Verify HMAC-SHA256 signature verification for Telegram WebApp."""
    test_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    valid_init_data = generate_valid_init_data(user_id=888999, bot_token=test_token)

    user = validate_telegram_init_data(valid_init_data, test_token)
    assert user is not None
    assert user.id == 888999
    assert user.first_name == "Admin"

    # Test tampering
    tampered = valid_init_data.replace("888999", "777666")
    invalid_user = validate_telegram_init_data(tampered, test_token)
    assert invalid_user is None


@pytest.mark.asyncio
async def test_api_health_check():
    """Verify FastAPI /health endpoint returns 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_get_and_patch_chat_settings(db_session: AsyncSession):
    """Verify chat settings retrieval and modification via REST API."""
    chat = Chat(
        chat_id=-100654321,
        title="API Managed Community",
        ai_confidence_threshold=80.0,
        captcha_enabled=True,
        whitelisted_users=[999],
    )
    db_session.add(chat)
    await db_session.commit()

    # Override dependencies for test
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_telegram_user] = lambda: TelegramUser(id=999, first_name="Admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET Settings
        res_get = await client.get("/api/chats/-100654321")
        assert res_get.status_code == 200
        data = res_get.json()
        assert data["title"] == "API Managed Community"
        assert data["ai_confidence_threshold"] == 80.0

        # 2. PATCH Settings
        res_patch = await client.patch(
            "/api/chats/-100654321",
            json={"ai_confidence_threshold": 92.5, "clean_service_messages": True},
        )
        assert res_patch.status_code == 200
        patched_data = res_patch.json()
        assert patched_data["ai_confidence_threshold"] == 92.5
        assert patched_data["clean_service_messages"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_stats_and_logs(db_session: AsyncSession):
    """Verify statistics aggregation and audit log history endpoint."""
    chat = Chat(
        chat_id=-100777111,
        title="Stats Community",
        whitelisted_users=[999],
    )
    user = User(chat_id=-100777111, telegram_id=123, first_name="Offender")
    db_session.add_all([chat, user])
    await db_session.commit()

    log = AuditLog(
        chat_id=-100777111,
        user_id=user.id,
        action_type="ban_user",
        category="crypto_scam",
        reason="Airdrop scam",
        confidence=98.0,
    )
    db_session.add(log)
    await db_session.commit()

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_telegram_user] = lambda: TelegramUser(id=999, first_name="Admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET Stats
        res_stats = await client.get("/api/stats/-100777111")
        assert res_stats.status_code == 200
        stats_data = res_stats.json()
        assert stats_data["total_violations"] == 1
        assert stats_data["total_bans"] == 1

        # GET Logs
        res_logs = await client.get("/api/stats/-100777111/logs")
        assert res_logs.status_code == 200
        logs_data = res_logs.json()
        assert len(logs_data) == 1
        assert logs_data[0]["category"] == "crypto_scam"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unauthorized_chat_access(db_session: AsyncSession):
    """Verify that unauthorized users receive 403 Forbidden on chat endpoints."""
    chat = Chat(
        chat_id=-100888999,
        title="Private Admin Group",
        whitelisted_users=[111],
    )
    db_session.add(chat)
    await db_session.commit()

    # User 999 is NOT superadmin and NOT in whitelisted_users
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_telegram_user] = lambda: TelegramUser(id=999, first_name="Stranger")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET Settings -> 403
        res = await client.get("/api/chats/-100888999")
        assert res.status_code == 403

        # PATCH Settings -> 403
        res_patch = await client.patch("/api/chats/-100888999", json={"warn_limit": 5})
        assert res_patch.status_code == 403

        # GET Stats -> 403
        res_stats = await client.get("/api/stats/-100888999")
        assert res_stats.status_code == 403

    app.dependency_overrides.clear()

"""Shared API fixtures: real repositories and an isolated database per test."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.models.user import User  # noqa: F401
from src.models.agent import Agent  # noqa: F401
from src.models.message import Message  # noqa: F401 - register metadata
from src.core.database import Base, get_db_session
from src.models.conversation import Conversation  # noqa: F401 - register metadata
from src.models.customer import Customer  # noqa: F401 - register metadata


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        # SQLite does not enforce foreign keys by default; PostgreSQL does.
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest.fixture
async def anonymous_client(session_factory):
    # Import here so service-only tests remain runnable if route registration fails.
    from src.main import app
    from src.core.config import Settings, get_settings

    async def session_override():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, jwt_secret_key="test-only-secret-key-not-for-production-123456-more-entropy")
    try:
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as http_client:
                yield http_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
async def admin_user(session_factory):
    from src.core.security import hash_password
    from src.domain.enums import UserRole
    async with session_factory() as session:
        user = User(email="admin@example.com", password_hash=hash_password("Admin-test-password-123!"), role=UserRole.ADMIN)
        session.add(user)
        await session.commit()
        return user


@pytest.fixture
async def client(anonymous_client, admin_user):
    response = await anonymous_client.post("/api/v1/auth/login", json={
        "email": admin_user.email, "password": "Admin-test-password-123!",
    })
    assert response.status_code == 200, response.text
    anonymous_client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
    yield anonymous_client
    anonymous_client.headers.pop("Authorization", None)

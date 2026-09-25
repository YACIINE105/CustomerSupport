"""Shared API fixtures: real repositories and an isolated database per test."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import Base, get_db_session
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
async def client(session_factory):
    # Import here so service-only tests remain runnable if route registration fails.
    from src.main import app

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
    try:
        async with app.router.lifespan_context(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as http_client:
                yield http_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

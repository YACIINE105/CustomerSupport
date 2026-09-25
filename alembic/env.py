"""Run migrations with the same configuration and metadata as the application."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.models.escalation import Escalation  # noqa: F401
from src.models.user import User  # noqa: F401
from src.models.agent import Agent  # noqa: F401
from src.models.message import Message  # noqa: F401 - register metadata
from src.core.database import Base
from src.models.customer import Customer  # noqa: F401 — registers the table
from src.models.conversation import Conversation


target_metadata = Base.metadata


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_online():
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_online())

from unittest.mock import AsyncMock

import pytest

from src.core.config import Settings
from src.core.exceptions import ConflictError, PermissionDeniedError
from src.domain.enums import UserRole
from src.models.user import User
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository
from src.schemas.auth import UserCreate
from src.services.auth_service import AuthService


async def test_non_admin_cannot_provision_accounts():
    users = AsyncMock(spec=UserRepository)
    service = AuthService(users, AsyncMock(spec=AgentRepository), Settings(_env_file=None))
    with pytest.raises(PermissionDeniedError):
        await service.register(
            UserCreate(email='new@example.com', password='Long-test-password'),
            User(id=7, role=UserRole.AGENT),
        )
    users.create.assert_not_awaited()


async def test_bootstrap_creates_first_admin_once(session_factory):
    data = UserCreate(email='first@example.com', password='Long-test-password', role='ADMIN')
    async with session_factory() as session:
        service = AuthService(UserRepository(session), AgentRepository(session), Settings(_env_file=None))
        user = await service.bootstrap_admin(data)
        assert user.role == UserRole.ADMIN
        assert user.password_hash != data.password.get_secret_value()
        await session.commit()
        with pytest.raises(ConflictError):
            await service.bootstrap_admin(data)

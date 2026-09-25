import logging

from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from src.core.config import Settings
from src.core.exceptions import AuthenticationError, ConflictError, PermissionDeniedError, ResourceNotFoundError
from src.core.security import create_access_token, hash_password, signing_key, verify_password
from src.domain.enums import AgentStatus, UserRole
from src.models.user import User
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository
from src.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, users: UserRepository, agents: AgentRepository, settings: Settings) -> None:
        self.users, self.agents, self.settings = users, agents, settings

    async def register(self, data: UserCreate, actor: User) -> User:
        if actor.role != UserRole.ADMIN:
            raise PermissionDeniedError()
        user = await self._create_user(data)
        logger.info("user.created actor_id=%s user_id=%s role=%s", actor.id, user.id, user.role)
        return user

    async def _create_user(self, data: UserCreate) -> User:
        if await self.users.get_by_email(str(data.email)):
            raise ConflictError("Email is already registered")
        password_hash = await run_in_threadpool(hash_password, data.password.get_secret_value())
        try:
            return await self.users.create(data, password_hash)
        except IntegrityError as exc:
            raise ConflictError("Email is already registered") from exc

    async def bootstrap_admin(self, data: UserCreate) -> User:
        if data.role != UserRole.ADMIN or await self.users.has_admin():
            raise ConflictError("An administrator already exists or an invalid role was supplied")
        return await self._create_user(data)

    async def login(self, data: LoginRequest) -> TokenResponse:
        signing_key(self.settings)
        user = await self.users.get_by_email(str(data.email))
        valid = await run_in_threadpool(
            verify_password, data.password.get_secret_value(), user.password_hash if user else None,
        )
        if not valid or user is None or not user.is_active:
            raise AuthenticationError()
        return TokenResponse(
            access_token=create_access_token(user.id, self.settings),
            expires_in=self.settings.access_token_expire_minutes * 60,
        )

    async def list_users(self, *, offset: int, limit: int) -> list[User]:
        return await self.users.list(offset=offset, limit=limit)

    async def update_user(self, user_id: int, data: UserUpdate, actor: User) -> User:
        if actor.role != UserRole.ADMIN:
            raise PermissionDeniedError()
        user = await self.users.get(user_id)
        if user is None:
            raise ResourceNotFoundError("User", user_id)
        if user.id == actor.id and (data.is_active is False or (data.role and data.role != UserRole.ADMIN)):
            raise ConflictError("You cannot disable or demote your own administrator account")
        agent = await self.agents.get_by_user(user.id)
        if agent and data.role is not None and data.role != UserRole.AGENT:
            raise ConflictError("A user with an agent profile must retain the AGENT role")
        if agent and data.is_active is False:
            await self.agents.set_status(agent, AgentStatus.OFFLINE)
        result = await self.users.update(user, data)
        logger.info("user.updated actor_id=%s user_id=%s", actor.id, user.id)
        return result

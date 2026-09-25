import logging

from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictError, PermissionDeniedError, ResourceNotFoundError
from src.domain.enums import UserRole
from src.models.agent import Agent
from src.models.user import User
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository
from src.schemas.agent import AgentCreate, AgentStatusUpdate

logger = logging.getLogger(__name__)
MANAGER_ROLES = {UserRole.ADMIN, UserRole.SUPPORT_HEAD}


class AgentService:
    def __init__(self, agents: AgentRepository, users: UserRepository) -> None:
        self.agents, self.users = agents, users

    async def create(self, data: AgentCreate, actor: User) -> Agent:
        if actor.role not in MANAGER_ROLES:
            raise PermissionDeniedError()
        user = await self.users.get(data.user_id)
        if user is None:
            raise ResourceNotFoundError("User", data.user_id)
        if user.role != UserRole.AGENT or not user.is_active:
            raise ConflictError("Agent profiles require an active user with the AGENT role")
        if await self.agents.get_by_user(user.id):
            raise ConflictError("User already has an agent profile")
        try:
            agent = await self.agents.create(data)
        except IntegrityError as exc:
            raise ConflictError("User is unavailable or already has an agent profile") from exc
        logger.info("agent.created actor_id=%s agent_id=%s", actor.id, agent.id)
        return agent

    async def get(self, agent_id: int) -> Agent:
        agent = await self.agents.get(agent_id)
        if agent is None:
            raise ResourceNotFoundError("Agent", agent_id)
        return agent

    async def list(self, *, offset: int, limit: int) -> list[Agent]:
        return await self.agents.list(offset=offset, limit=limit)

    async def update_status(self, agent_id: int, data: AgentStatusUpdate, actor: User) -> Agent:
        agent = await self.get(agent_id)
        if actor.role not in MANAGER_ROLES and agent.user_id != actor.id:
            raise PermissionDeniedError()
        user = await self.users.get(agent.user_id)
        if user is None or not user.is_active:
            raise ConflictError("Inactive users cannot change agent availability")
        agent = await self.agents.set_status(agent, data.status)
        logger.info("agent.status_changed actor_id=%s agent_id=%s status=%s", actor.id, agent.id, agent.status)
        return agent

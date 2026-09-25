from src.models.agent import Agent
from src.models.user import User
from src.schemas.agent import AgentCreate, AgentStatusUpdate
from src.services.agent_service import AgentService


class AgentController:
    def __init__(self, service: AgentService) -> None:
        self.service = service

    async def create(self, data: AgentCreate, actor: User) -> Agent:
        return await self.service.create(data, actor)

    async def get(self, agent_id: int) -> Agent:
        return await self.service.get(agent_id)

    async def list(self, *, offset: int, limit: int) -> list[Agent]:
        return await self.service.list(offset=offset, limit=limit)

    async def update_status(self, agent_id: int, data: AgentStatusUpdate, actor: User) -> Agent:
        return await self.service.update_status(agent_id, data, actor)

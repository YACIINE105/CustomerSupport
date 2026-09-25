from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AgentStatus
from src.models.agent import Agent
from src.schemas.agent import AgentCreate


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, agent_id: int) -> Agent | None:
        return await self.session.get(Agent, agent_id)

    async def get_by_user(self, user_id: int) -> Agent | None:
        return await self.session.scalar(select(Agent).where(Agent.user_id == user_id))

    async def list(self, *, offset: int, limit: int) -> list[Agent]:
        return list((await self.session.scalars(select(Agent).order_by(Agent.id).offset(offset).limit(limit))).all())

    async def create(self, data: AgentCreate) -> Agent:
        agent = Agent(**data.model_dump())
        self.session.add(agent)
        await self.session.flush()
        await self.session.refresh(agent)
        return agent

    async def set_status(self, agent: Agent, status: AgentStatus) -> Agent:
        agent.status = status
        await self.session.flush()
        await self.session.refresh(agent)
        return agent

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.controllers.agent_controller import AgentController
from src.core.dependencies import CurrentUser, ManagerUser, SessionDependency
from src.models.agent import Agent
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository
from src.schemas.agent import AgentCreate, AgentResponse, AgentStatusUpdate
from src.services.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


def get_agent_controller(session: SessionDependency) -> AgentController:
    return AgentController(AgentService(AgentRepository(session), UserRepository(session)))


Controller = Annotated[AgentController, Depends(get_agent_controller)]


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(data: AgentCreate, actor: ManagerUser, controller: Controller) -> Agent:
    return await controller.create(data, actor)


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    actor: CurrentUser, controller: Controller,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Agent]:
    return await controller.list(offset=offset, limit=limit)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, actor: CurrentUser, controller: Controller) -> Agent:
    return await controller.get(agent_id)


@router.patch("/{agent_id}/status", response_model=AgentResponse)
async def update_status(agent_id: int, data: AgentStatusUpdate, actor: CurrentUser, controller: Controller) -> Agent:
    return await controller.update_status(agent_id, data, actor)

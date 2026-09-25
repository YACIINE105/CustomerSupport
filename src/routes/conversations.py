from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.conversation_controller import ConversationController
from src.core.database import get_db_session
from src.core.dependencies import CurrentUser, ManagerUser
from src.domain.enums import ConversationChannel, ConversationStatus
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository
from src.schemas.conversation import ConversationUpdate, ConversationAssign
from src.models.conversation import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.customer_repository import CustomerRepository
from src.schemas.conversation import ConversationCreate, ConversationResponse
from src.services.conversation_service import ConversationService


router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_controller(session: Annotated[AsyncSession,
                            Depends(get_db_session, scope="function")],) -> ConversationController:

    repository = ConversationRepository(session)
    service = ConversationService(repository, CustomerRepository(session), AgentRepository(session), UserRepository(session))
    return ConversationController(service)


ControllerDependency = Annotated[
    ConversationController,
    Depends(get_conversation_controller),]


@router.post("",response_model=ConversationResponse,
             status_code=status.HTTP_201_CREATED,)


async def create_conversation(data:ConversationCreate,
                        controller:ControllerDependency)->Conversation:
    return await controller.create(data=data)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id:int,
                           controller:ControllerDependency)-> Conversation:

    return await controller.get(conversation_id=conversation_id)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    controller: ControllerDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    status: ConversationStatus | None = None,
    customer_id: Annotated[int | None, Query(gt=0)] = None,
    assigned_agent_id: Annotated[int | None, Query(gt=0)] = None,
    channel: ConversationChannel | None = None,
):
    return await controller.list(offset=offset, limit=limit, status=status,
                                 customer_id=customer_id, assigned_agent_id=assigned_agent_id, channel=channel)


@router.post("/{conversation_id}/assign", response_model=ConversationResponse)
async def assign(conversation_id: int, data: ConversationAssign, actor: ManagerUser, controller: ControllerDependency):
    return await controller.assign(conversation_id, data.agent_id, actor)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update(conversation_id: int, data: ConversationUpdate, actor: CurrentUser, controller: ControllerDependency):
    return await controller.transition(conversation_id, data.status, actor)


@router.post("/{conversation_id}/resolve", response_model=ConversationResponse)
async def resolve(conversation_id: int, actor: CurrentUser, controller: ControllerDependency):
    return await controller.transition(conversation_id, ConversationStatus.RESOLVED, actor)


@router.post("/{conversation_id}/close", response_model=ConversationResponse)
async def close(conversation_id: int, actor: CurrentUser, controller: ControllerDependency):
    return await controller.transition(conversation_id, ConversationStatus.CLOSED, actor)

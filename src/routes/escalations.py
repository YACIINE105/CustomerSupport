from typing import Annotated
from fastapi import APIRouter, Depends, Query
from src.core.dependencies import CurrentUser, SessionDependency
from src.controllers.escalation_controller import EscalationController
from src.domain.enums import EscalationStatus, EscalationPriority
from src.repositories.escalation_repository import EscalationRepository
from src.routes.conversations import get_conversation_controller
from src.schemas.escalation import EscalationCreate, EscalationResponse, EscalationUpdate
from src.services.escalation_service import EscalationService

router = APIRouter(prefix="/escalations", tags=["escalations"])


def get_controller(session: SessionDependency):
    return EscalationController(EscalationService(EscalationRepository(session), get_conversation_controller(session).service))


Controller = Annotated[EscalationController, Depends(get_controller)]


@router.post("", response_model=EscalationResponse, status_code=201)
async def create(data: EscalationCreate, actor: CurrentUser, controller: Controller):
    return await controller.create(data, actor)


@router.get("", response_model=list[EscalationResponse])
async def list_escalations(
    actor: CurrentUser, controller: Controller,
    offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 100,
    conversation_id: Annotated[int | None, Query(gt=0)] = None,
    assigned_agent_id: Annotated[int | None, Query(gt=0)] = None,
    status: EscalationStatus | None = None, priority: EscalationPriority | None = None,
):
    return await controller.list(offset=offset, limit=limit, conversation_id=conversation_id,
                                 assigned_agent_id=assigned_agent_id, status=status, priority=priority)


@router.get("/{escalation_id}", response_model=EscalationResponse)
async def get(escalation_id: int, actor: CurrentUser, controller: Controller):
    return await controller.get(escalation_id)


@router.patch("/{escalation_id}", response_model=EscalationResponse)
async def update(escalation_id: int, data: EscalationUpdate, actor: CurrentUser, controller: Controller):
    return await controller.update(escalation_id, data, actor)

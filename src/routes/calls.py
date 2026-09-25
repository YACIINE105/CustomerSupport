from typing import Annotated
from fastapi import APIRouter, Depends, Query
from src.core.dependencies import CurrentUser, SessionDependency
from src.controllers.call_controller import CallController
from src.domain.enums import CallDirection, CallStatus
from src.repositories.call_repository import CallRepository
from src.routes.conversations import get_conversation_controller
from src.schemas.call import CallCreate, CallResponse, CallUpdate
from src.services.call_service import CallService

router = APIRouter(prefix="/calls", tags=["calls"])


def get_controller(session: SessionDependency):
    return CallController(CallService(CallRepository(session), get_conversation_controller(session).service))


Controller = Annotated[CallController, Depends(get_controller)]


@router.post("", response_model=CallResponse, status_code=201)
async def create(data: CallCreate, actor: CurrentUser, controller: Controller):
    return await controller.create(data, actor)


@router.get("", response_model=list[CallResponse])
async def list_calls(
    actor: CurrentUser, controller: Controller,
    offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 100,
    conversation_id: Annotated[int | None, Query(gt=0)] = None,
    agent_id: Annotated[int | None, Query(gt=0)] = None,
    status: CallStatus | None = None, direction: CallDirection | None = None,
):
    return await controller.list(offset=offset, limit=limit, conversation_id=conversation_id,
                                 agent_id=agent_id, status=status, direction=direction)


@router.get("/{call_id}", response_model=CallResponse)
async def get(call_id: int, actor: CurrentUser, controller: Controller):
    return await controller.get(call_id)


@router.patch("/{call_id}", response_model=CallResponse)
async def update(call_id: int, data: CallUpdate, actor: CurrentUser, controller: Controller):
    return await controller.update(call_id, data, actor)

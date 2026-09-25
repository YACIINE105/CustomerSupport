from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.message_controller import MessageController
from src.core.database import get_db_session
from src.models.message import Message
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.schemas.message import MessageCreate, MessageResponse
from src.services.message_service import MessageService

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["messages"])


def get_message_controller(
    session: Annotated[AsyncSession, Depends(get_db_session, scope="function")],
) -> MessageController:
    return MessageController(MessageService(MessageRepository(session), ConversationRepository(session)))


ControllerDependency = Annotated[MessageController, Depends(get_message_controller)]


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: int, data: MessageCreate, controller: ControllerDependency,
) -> Message:
    return await controller.create(conversation_id, data)


@router.get("", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: int,
    controller: ControllerDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Message]:
    return await controller.list(conversation_id, offset=offset, limit=limit)

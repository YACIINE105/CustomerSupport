from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.controllers.conversation_controller import ConversationController
from src.core.database import get_db_session
from src.models.conversation import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.customer_repository import CustomerRepository
from src.schemas.conversation import ConversationCreate, ConversationResponse
from src.services.conversation_service import ConversationService


router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_controller(session: Annotated[AsyncSession,
                            Depends(get_db_session, scope="function")],) -> ConversationController:

    repository = ConversationRepository(session)
    service = ConversationService(repository, CustomerRepository(session))
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

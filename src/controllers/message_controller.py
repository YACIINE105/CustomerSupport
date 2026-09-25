from src.models.message import Message
from src.models.user import User
from src.schemas.message import MessageCreate
from src.services.message_service import MessageService


class MessageController:
    def __init__(self, service: MessageService) -> None:
        self.service = service

    async def create(self, conversation_id: int, data: MessageCreate, actor: User) -> Message:
        return await self.service.create_message(conversation_id, data, actor)

    async def list(self, conversation_id: int, *, offset: int, limit: int) -> list[Message]:
        return await self.service.list_messages(conversation_id, offset=offset, limit=limit)

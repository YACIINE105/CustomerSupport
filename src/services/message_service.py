from src.core.exceptions import ApplicationError, ResourceNotFoundError
from src.models.conversation import Conversation
from src.models.message import Message
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.schemas.message import MessageCreate


class MessageService:
    def __init__(self, repository: MessageRepository, conversations: ConversationRepository) -> None:
        self.repository = repository
        self.conversations = conversations

    async def _get_conversation(self, conversation_id: int) -> Conversation:
        conversation = await self.conversations.get(conversation_id)
        if conversation is None:
            raise ResourceNotFoundError("Conversation", conversation_id)
        return conversation

    async def create_message(self, conversation_id: int, data: MessageCreate) -> Message:
        conversation = await self._get_conversation(conversation_id)
        if data.sender_id != conversation.customer_id:
            raise ApplicationError(
                "Message sender must be the conversation's customer",
                status_code=422,
                code="invalid_message_sender",
            )
        return await self.repository.create(conversation_id, data)

    async def list_messages(self, conversation_id: int, *, offset: int, limit: int) -> list[Message]:
        await self._get_conversation(conversation_id)
        return await self.repository.list(conversation_id, offset=offset, limit=limit)

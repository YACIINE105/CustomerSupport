from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import ConversationStatus
from src.models.conversation import Conversation
from src.schemas.conversation import ConversationCreate


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self,data: ConversationCreate,status: ConversationStatus,) -> Conversation:
        conversation = Conversation(
            **data.model_dump(),
            status=status.value,
        )

        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)

        return conversation

    async def get(self, conversation_id: int) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

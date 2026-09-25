from sqlalchemy import select
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


    async def get_for_update(self, conversation_id: int) -> Conversation | None:
        return await self.session.scalar(
            select(Conversation).where(Conversation.id == conversation_id).with_for_update()
        )

    async def list(self, *, offset: int, limit: int, status=None, customer_id=None, assigned_agent_id=None, channel=None) -> list[Conversation]:
        query = select(Conversation)
        for field, value in {"status": status, "customer_id": customer_id,
                             "assigned_agent_id": assigned_agent_id, "channel": channel}.items():
            if value is not None:
                query = query.where(getattr(Conversation, field) == value)
        return list((await self.session.scalars(query.order_by(Conversation.id).offset(offset).limit(limit))).all())

    async def save(self, conversation: Conversation) -> Conversation:
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

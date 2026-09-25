from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.message import Message
from src.schemas.message import MessageCreate


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, conversation_id: int, data: MessageCreate) -> Message:
        values = data.model_dump(exclude={"metadata"})
        message = Message(
            conversation_id=conversation_id, **values, message_metadata=data.metadata,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def list(self, conversation_id: int, *, offset: int, limit: int) -> list[Message]:
        result = await self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

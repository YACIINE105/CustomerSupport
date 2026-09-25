from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.call import Call


class CallRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, call_id, *, lock=False):
        query = select(Call).where(Call.id == call_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return await self.session.scalar(query)

    async def for_conversation(self, conversation_id):
        return await self.session.scalar(select(Call).where(Call.conversation_id == conversation_id))

    async def create(self, data, agent_id):
        item = Call(**data.model_dump(exclude={"agent_id"}), agent_id=agent_id)
        self.session.add(item)
        return await self.save(item)

    async def save(self, item):
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def list(self, *, offset, limit, **filters):
        query = select(Call)
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(Call, field) == value)
        return list((await self.session.scalars(query.order_by(Call.id).offset(offset).limit(limit))).all())

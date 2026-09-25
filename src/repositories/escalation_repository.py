from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.escalation import Escalation
from src.domain.enums import EscalationStatus


class EscalationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, escalation_id, *, lock=False):
        query = select(Escalation).where(Escalation.id == escalation_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        return await self.session.scalar(query)

    async def active(self, conversation_id):
        return await self.session.scalar(select(Escalation).where(
            Escalation.conversation_id == conversation_id, Escalation.status != EscalationStatus.RESOLVED))

    async def create(self, data, status):
        escalation = Escalation(**data.model_dump(), status=status)
        self.session.add(escalation)
        return await self.save(escalation)

    async def save(self, escalation):
        await self.session.flush()
        await self.session.refresh(escalation)
        return escalation

    async def list(self, *, offset, limit, **filters):
        query = select(Escalation)
        for key, value in filters.items():
            if value is not None:
                query = query.where(getattr(Escalation, key) == value)
        return list((await self.session.scalars(query.order_by(Escalation.id).offset(offset).limit(limit))).all())

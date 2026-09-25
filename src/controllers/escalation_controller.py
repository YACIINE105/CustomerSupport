from src.services.escalation_service import EscalationService


class EscalationController:
    def __init__(self, service: EscalationService):
        self.service = service

    async def create(self, data, actor):
        return await self.service.create(data, actor)

    async def get(self, escalation_id):
        return await self.service.get(escalation_id)

    async def list(self, **filters):
        return await self.service.list(**filters)

    async def update(self, escalation_id, data, actor):
        return await self.service.update(escalation_id, data, actor)

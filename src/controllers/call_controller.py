from src.services.call_service import CallService


class CallController:
    def __init__(self, service: CallService):
        self.service = service

    async def create(self, data, actor):
        return await self.service.create(data, actor)

    async def get(self, call_id):
        return await self.service.get(call_id)

    async def list(self, **filters):
        return await self.service.list(**filters)

    async def update(self, call_id, data, actor):
        return await self.service.update(call_id, data, actor)

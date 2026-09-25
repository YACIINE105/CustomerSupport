from src.models.conversation import Conversation
from src.schemas.conversation import ConversationCreate
from src.services.conversation_service import ConversationService



class ConversationController:
    def __init__(self, service: ConversationService) -> None:
            self.service = service


    async def create(self, data: ConversationCreate) -> Conversation:
        return await self.service.create_conversation(data=data)


    async def get(self, conversation_id:int)->Conversation:
        return await self.service.get_conversation(conversation_id=conversation_id)


    async def list(self, **filters):
        return await self.service.list_conversations(**filters)

    async def assign(self, conversation_id, agent_id, actor):
        return await self.service.assign(conversation_id, agent_id, actor)

    async def transition(self, conversation_id, status, actor):
        return await self.service.transition(conversation_id, status, actor)

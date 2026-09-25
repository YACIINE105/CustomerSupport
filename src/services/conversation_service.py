from src.core.exceptions import ResourceNotFoundError
from src.domain.enums import ConversationStatus
from src.models.conversation import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.customer_repository import CustomerRepository
from src.schemas.conversation import ConversationCreate


class ConversationService:
    def __init__(self,conversation_repository: ConversationRepository,
                 customer_repository: CustomerRepository,) -> None:

        self.conversation_repository = conversation_repository
        self.customer_repository = customer_repository

    async def create_conversation(self,data: ConversationCreate,) -> Conversation:

        customer = await self.customer_repository.get(data.customer_id)

        if customer is None:
            raise ResourceNotFoundError("Customer", data.customer_id)

        return await self.conversation_repository.create(
            data,
            status=ConversationStatus.OPEN,
        )

    async def get_conversation(self,conversation_id: int,) -> Conversation:

        conversation = await self.conversation_repository.get(conversation_id)

        if conversation is None:
            raise ResourceNotFoundError(
                "Conversation",
                conversation_id,
            )

        return conversation

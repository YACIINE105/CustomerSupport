import logging
from datetime import datetime, timezone

from src.core.exceptions import ConflictError, PermissionDeniedError, ResourceNotFoundError
from src.domain.enums import AgentStatus, UserRole, ConversationStatus
from src.models.user import User
from src.repositories.agent_repository import AgentRepository
from src.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)
TRANSITIONS = {
    ConversationStatus.OPEN: {ConversationStatus.IN_PROGRESS, ConversationStatus.WAITING, ConversationStatus.RESOLVED},
    ConversationStatus.IN_PROGRESS: {ConversationStatus.WAITING, ConversationStatus.RESOLVED},
    ConversationStatus.WAITING: {ConversationStatus.IN_PROGRESS, ConversationStatus.RESOLVED},
    ConversationStatus.RESOLVED: {ConversationStatus.CLOSED},
    ConversationStatus.CLOSED: set(),
    ConversationStatus.ESCALATED: set(),
}
from src.models.conversation import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.customer_repository import CustomerRepository
from src.schemas.conversation import ConversationCreate


class ConversationService:
    def __init__(self,conversation_repository: ConversationRepository,
                 customer_repository: CustomerRepository,
                 agents: AgentRepository | None = None, users: UserRepository | None = None) -> None:

        self.agents, self.users = agents, users
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


    async def list_conversations(self, **filters) -> list[Conversation]:
        return await self.conversation_repository.list(**filters)

    async def locked(self, conversation_id: int) -> Conversation:
        conversation = await self.conversation_repository.get_for_update(conversation_id)
        if conversation is None:
            raise ResourceNotFoundError("Conversation", conversation_id)
        return conversation

    async def authorize_change(self, conversation: Conversation, actor: User) -> None:
        if actor.role in {UserRole.ADMIN, UserRole.SUPPORT_HEAD}:
            return
        agent = await self.agents.get_by_user(actor.id) if self.agents else None
        if agent is None or conversation.assigned_agent_id != agent.id:
            raise PermissionDeniedError()

    async def eligible_agent(self, agent_id: int):
        agent = await self.agents.get(agent_id)
        if agent is None:
            raise ResourceNotFoundError("Agent", agent_id)
        user = await self.users.get(agent.user_id)
        if user is None or not user.is_active or agent.status != AgentStatus.AVAILABLE:
            raise ConflictError("Assignment requires an active, AVAILABLE agent")
        return agent

    async def assign(self, conversation_id: int, agent_id: int, actor: User) -> Conversation:
        if actor.role not in {UserRole.ADMIN, UserRole.SUPPORT_HEAD}:
            raise PermissionDeniedError()
        conversation = await self.locked(conversation_id)
        if conversation.status in {ConversationStatus.RESOLVED, ConversationStatus.CLOSED}:
            raise ConflictError("Cannot assign a resolved or closed conversation")
        await self.eligible_agent(agent_id)
        conversation.assigned_agent_id = agent_id
        if conversation.status == ConversationStatus.OPEN:
            conversation.status = ConversationStatus.IN_PROGRESS
        logger.info("conversation.assigned actor_id=%s conversation_id=%s agent_id=%s", actor.id, conversation_id, agent_id)
        return await self.conversation_repository.save(conversation)

    async def transition(self, conversation_id: int, status: ConversationStatus, actor: User) -> Conversation:
        conversation = await self.locked(conversation_id)
        await self.authorize_change(conversation, actor)
        if conversation.status == status:
            return conversation
        if status not in TRANSITIONS[conversation.status]:
            raise ConflictError(f"Cannot move conversation from {conversation.status} to {status}")
        conversation.status = status
        if status == ConversationStatus.RESOLVED:
            conversation.ended_at = datetime.now(timezone.utc)
        logger.info("conversation.status_changed actor_id=%s conversation_id=%s status=%s", actor.id, conversation_id, status)
        return await self.conversation_repository.save(conversation)

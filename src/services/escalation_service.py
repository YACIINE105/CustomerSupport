import logging
from datetime import datetime, timezone
from src.core.exceptions import ConflictError, PermissionDeniedError, ResourceNotFoundError
from src.domain.enums import ConversationStatus, EscalationStatus, UserRole

logger = logging.getLogger(__name__)
MANAGERS = {UserRole.ADMIN, UserRole.SUPPORT_HEAD}


class EscalationService:
    def __init__(self, repository, conversations):
        self.repository, self.conversations = repository, conversations

    async def get(self, escalation_id):
        item = await self.repository.get(escalation_id)
        if item is None:
            raise ResourceNotFoundError("Escalation", escalation_id)
        return item

    async def list(self, **filters):
        return await self.repository.list(**filters)

    async def create(self, data, actor):
        conversation = await self.conversations.locked(data.conversation_id)
        await self.conversations.authorize_change(conversation, actor)
        if conversation.status in {ConversationStatus.RESOLVED, ConversationStatus.CLOSED}:
            raise ConflictError("Cannot escalate a resolved or closed conversation")
        if await self.repository.active(conversation.id):
            raise ConflictError("Conversation already has an unresolved escalation")
        if data.assigned_agent_id is not None:
            if actor.role not in MANAGERS:
                raise PermissionDeniedError()
            await self.conversations.eligible_agent(data.assigned_agent_id)
            conversation.assigned_agent_id = data.assigned_agent_id
        item = await self.repository.create(data, EscalationStatus.ASSIGNED if data.assigned_agent_id else EscalationStatus.OPEN)
        conversation.status = ConversationStatus.ESCALATED
        await self.conversations.conversation_repository.save(conversation)
        logger.info("conversation.escalated actor_id=%s conversation_id=%s escalation_id=%s", actor.id, conversation.id, item.id)
        return item

    async def update(self, escalation_id, data, actor):
        original = await self.get(escalation_id)
        conversation = await self.conversations.locked(original.conversation_id)
        item = await self.repository.get(escalation_id, lock=True)
        changes = data.model_dump(exclude_unset=True)
        if actor.role not in MANAGERS:
            agent = await self.conversations.agents.get_by_user(actor.id)
            if agent is None or agent.id != item.assigned_agent_id or set(changes) - {"status"}:
                raise PermissionDeniedError()
        if item.status == EscalationStatus.RESOLVED:
            if changes == {"status": EscalationStatus.RESOLVED} or not changes:
                return item
            raise ConflictError("Resolved escalations cannot be edited")
        if "assigned_agent_id" in changes:
            agent_id = changes["assigned_agent_id"]
            if agent_id is not None:
                await self.conversations.eligible_agent(agent_id)
                conversation.assigned_agent_id = agent_id
            item.assigned_agent_id = agent_id
            item.status = EscalationStatus.ASSIGNED if agent_id else EscalationStatus.OPEN
        if "priority" in changes:
            item.priority = data.priority
        if data.status == EscalationStatus.RESOLVED:
            item.status = EscalationStatus.RESOLVED
            item.resolved_at = datetime.now(timezone.utc)
            conversation.status = ConversationStatus.IN_PROGRESS if conversation.assigned_agent_id else ConversationStatus.OPEN
        await self.conversations.conversation_repository.save(conversation)
        logger.info("escalation.updated actor_id=%s escalation_id=%s status=%s", actor.id, item.id, item.status)
        return await self.repository.save(item)

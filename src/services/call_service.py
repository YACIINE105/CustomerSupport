import logging
from datetime import datetime, timezone
from src.core.exceptions import ConflictError, PermissionDeniedError, ResourceNotFoundError
from src.domain.enums import CallStatus, ConversationChannel, ConversationStatus, UserRole

logger = logging.getLogger(__name__)
TRANSITIONS = {
    CallStatus.INITIATED: {CallStatus.RINGING, CallStatus.ANSWERED, CallStatus.FAILED, CallStatus.CANCELLED},
    CallStatus.RINGING: {CallStatus.ANSWERED, CallStatus.MISSED, CallStatus.FAILED, CallStatus.CANCELLED},
    CallStatus.ANSWERED: {CallStatus.COMPLETED, CallStatus.FAILED},
}
TERMINAL = {CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.CANCELLED, CallStatus.MISSED}


class CallService:
    def __init__(self, repository, conversations):
        self.repository, self.conversations = repository, conversations

    async def get(self, call_id):
        item = await self.repository.get(call_id)
        if item is None:
            raise ResourceNotFoundError("Call", call_id)
        return item

    async def list(self, **filters):
        return await self.repository.list(**filters)

    async def create(self, data, actor):
        conversation = await self.conversations.locked(data.conversation_id)
        await self.conversations.authorize_change(conversation, actor)
        if conversation.channel not in {ConversationChannel.VOICE, ConversationChannel.PHONE}:
            raise ConflictError("Calls require a VOICE or PHONE conversation")
        if conversation.status in {ConversationStatus.RESOLVED, ConversationStatus.CLOSED}:
            raise ConflictError("Cannot create a call on a resolved or closed conversation")
        if await self.repository.for_conversation(conversation.id):
            raise ConflictError("Conversation already has a call record")
        agent_id = data.agent_id if data.agent_id is not None else conversation.assigned_agent_id
        if agent_id is not None:
            if conversation.assigned_agent_id is not None and agent_id != conversation.assigned_agent_id:
                raise ConflictError("Call agent must match the conversation assignment")
            await self.conversations.eligible_agent(agent_id)
        item = await self.repository.create(data, agent_id)
        logger.info("call.created actor_id=%s call_id=%s", actor.id, item.id)
        return item

    async def update(self, call_id, data, actor):
        original = await self.get(call_id)
        conversation = await self.conversations.locked(original.conversation_id)
        await self.conversations.authorize_change(conversation, actor)
        item = await self.repository.get(call_id, lock=True)
        changes = data.model_dump(exclude_unset=True)
        if data.status is not None and data.status != item.status:
            if data.status not in TRANSITIONS.get(item.status, set()):
                raise ConflictError(f"Cannot move call from {item.status} to {data.status}")
            now = datetime.now(timezone.utc)
            if data.status == CallStatus.ANSWERED:
                item.answered_at = now
            if data.status in TERMINAL:
                item.ended_at = now
                answered = item.answered_at
                if answered is not None:
                    if answered.tzinfo is None:
                        answered = answered.replace(tzinfo=timezone.utc)
                    item.duration_seconds = max(0, int((now - answered).total_seconds()))
            item.status = data.status
        for field in ("recording_url", "transcript"):
            if field in changes:
                value = changes[field]
                setattr(item, field, str(value) if value is not None else None)
        logger.info("call.updated actor_id=%s call_id=%s status=%s", actor.id, item.id, item.status)
        return await self.repository.save(item)

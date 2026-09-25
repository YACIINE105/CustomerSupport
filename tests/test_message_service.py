from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import ApplicationError, ResourceNotFoundError
from src.models.conversation import Conversation
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from src.schemas.message import MessageCreate
from src.services.message_service import MessageService


@pytest.fixture
def dependencies():
    messages = AsyncMock(spec=MessageRepository)
    conversations = AsyncMock(spec=ConversationRepository)
    return MessageService(messages, conversations), messages, conversations


@pytest.mark.parametrize("operation", ["create", "list"])
async def test_missing_conversation_prevents_repository_operation(dependencies, operation):
    service, messages, conversations = dependencies
    conversations.get.return_value = None
    with pytest.raises(ResourceNotFoundError):
        if operation == "create":
            await service.create_message(99, MessageCreate(sender_id=1, content="Hello"))
        else:
            await service.list_messages(99, offset=0, limit=100)
    conversations.get.assert_awaited_once_with(99)
    messages.create.assert_not_awaited()
    messages.list.assert_not_awaited()


async def test_mismatched_sender_prevents_creation(dependencies):
    service, messages, conversations = dependencies
    conversations.get.return_value = Conversation(id=7, customer_id=1)
    with pytest.raises(ApplicationError) as caught:
        await service.create_message(7, MessageCreate(sender_id=2, content="Hello"))
    assert caught.value.code == "invalid_message_sender"
    messages.create.assert_not_awaited()


async def test_creation_uses_matching_customer(dependencies):
    service, messages, conversations = dependencies
    conversations.get.return_value = Conversation(id=7, customer_id=1)
    data = MessageCreate(sender_id=1, content="Hello")
    assert await service.create_message(7, data) is messages.create.return_value
    messages.create.assert_awaited_once_with(7, data)


async def test_listing_preserves_pagination(dependencies):
    service, messages, conversations = dependencies
    conversations.get.return_value = Conversation(id=7, customer_id=1)
    messages.list.return_value = []
    assert await service.list_messages(7, offset=10, limit=20) == []
    messages.list.assert_awaited_once_with(7, offset=10, limit=20)

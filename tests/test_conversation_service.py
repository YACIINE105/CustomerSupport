"""Service contracts, independent of HTTP and database persistence."""

from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import ResourceNotFoundError
from src.domain.enums import ConversationChannel, ConversationStatus
from src.models.conversation import Conversation
from src.models.customer import Customer
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.customer_repository import CustomerRepository
from src.schemas.conversation import ConversationCreate
from src.services.conversation_service import ConversationService


@pytest.fixture
def dependencies():
    conversations = AsyncMock(spec=ConversationRepository)
    customers = AsyncMock(spec=CustomerRepository)
    service = ConversationService(conversations, customers)
    return service, conversations, customers


async def test_missing_customer_prevents_creation(dependencies):
    service, conversations, customers = dependencies
    customers.get.return_value = None
    data = ConversationCreate(customer_id=42, channel=ConversationChannel.CHAT)

    with pytest.raises(ResourceNotFoundError) as caught:
        await service.create_conversation(data)

    assert caught.value.status_code == 404
    assert caught.value.detail == "Customer with id 42 was not found"
    customers.get.assert_awaited_once_with(42)
    conversations.create.assert_not_awaited()


async def test_creation_starts_open_for_existing_customer(dependencies):
    service, conversations, customers = dependencies
    customers.get.return_value = Customer(id=42, name="Mona")
    stored = Conversation(
        id=7, customer_id=42, channel="CHAT", status="OPEN"
    )
    conversations.create.return_value = stored
    data = ConversationCreate(customer_id=42, channel=ConversationChannel.CHAT)

    result = await service.create_conversation(data)

    assert result is stored
    customers.get.assert_awaited_once_with(42)
    conversations.create.assert_awaited_once_with(
        data, status=ConversationStatus.OPEN
    )


async def test_missing_conversation_raises_not_found(dependencies):
    service, conversations, customers = dependencies
    conversations.get.return_value = None

    with pytest.raises(ResourceNotFoundError) as caught:
        await service.get_conversation(7)

    assert caught.value.status_code == 404
    assert caught.value.detail == "Conversation with id 7 was not found"
    conversations.get.assert_awaited_once_with(7)
    customers.get.assert_not_awaited()


async def test_get_returns_existing_conversation(dependencies):
    service, conversations, customers = dependencies
    stored = Conversation(id=7, customer_id=42, channel="CHAT", status="OPEN")
    conversations.get.return_value = stored

    assert await service.get_conversation(7) is stored

    conversations.get.assert_awaited_once_with(7)
    customers.get.assert_not_awaited()

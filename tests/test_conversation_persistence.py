"""Database safeguards that must hold even outside the HTTP service flow."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.models.conversation import Conversation
from src.models.customer import Customer


@pytest.mark.parametrize("load_children", [False, True])
async def test_customer_deletion_preserves_conversation_history(session_factory, load_children):
    async with session_factory() as session:
        customer = Customer(name="Mona")
        session.add(customer)
        await session.flush()
        conversation = Conversation(customer_id=customer.id, channel="CHAT")
        session.add(conversation)
        await session.commit()
        customer_id, conversation_id = customer.id, conversation.id
        assert conversation.status == "OPEN"

    async with session_factory() as session:
        statement = select(Customer).where(Customer.id == customer_id)
        if load_children:
            statement = statement.options(selectinload(Customer.conversations))
        customer = await session.scalar(statement)
        await session.delete(customer)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async with session_factory() as session:
        assert await session.get(Customer, customer_id) is not None
        assert await session.get(Conversation, conversation_id) is not None


@pytest.mark.parametrize("overrides", [{"channel": "EMAIL"}, {"status": "INVALID"}])
async def test_database_rejects_unknown_states(session_factory, overrides):
    async with session_factory() as session:
        customer = Customer(name="Mona")
        session.add(customer)
        await session.flush()
        session.add(Conversation(**{
            "customer_id": customer.id, "channel": "CHAT", "status": "OPEN", **overrides,
        }))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()

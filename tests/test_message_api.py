from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from src.models.message import Message


@pytest.fixture
async def conversation(client):
    response = await client.post('/api/v1/customers', json={'name': 'Mona'})
    assert response.status_code == 201
    customer_id = response.json()['id']
    response = await client.post('/api/v1/conversations', json={'customer_id': customer_id, 'channel': 'CHAT'})
    assert response.status_code == 201
    return response.json()


async def test_message_workflow_metadata_and_conversation_isolation(client, conversation, session_factory):
    path = f"/api/v1/conversations/{conversation['id']}/messages"
    assert (await client.get(path)).json() == []
    response = await client.post(path, json={
        'sender_id': conversation['customer_id'], 'content': '  Where is my order?  ',
        'metadata': {'order_id': 'A123', 'nested': {'tags': ['delivery'], 'urgent': False}},
    })
    assert response.status_code == 201, response.text
    message = response.json()
    assert message['content'] == 'Where is my order?'
    assert message['metadata']['nested']['tags'] == ['delivery']
    assert 'message_metadata' not in message
    assert message['sender_type'] == 'CUSTOMER'
    assert message['message_type'] == 'TEXT'
    assert message['conversation_id'] == conversation['id']
    assert message['sender_id'] == conversation['customer_id']
    datetime.fromisoformat(message['created_at'])
    assert (await client.get(path)).json() == [message]
    async with session_factory() as session:
        stored = await session.get(Message, message['id'])
        assert stored.message_metadata == message['metadata']

    second = (await client.post('/api/v1/conversations', json={
        'customer_id': conversation['customer_id'], 'channel': 'CHAT',
    })).json()
    assert (await client.get(f"/api/v1/conversations/{second['id']}/messages")).json() == []


async def test_timeline_orders_by_time_then_id_and_paginates(client, conversation, session_factory):
    # Insert out of chronological order, including equal timestamps.
    async with session_factory() as session:
        rows = [Message(
            conversation_id=conversation['id'], sender_type='CUSTOMER',
            sender_id=conversation['customer_id'], message_type='TEXT', content=content,
            created_at=datetime(2026, 1, day, tzinfo=timezone.utc),
        ) for day, content in [(2, 'later'), (1, 'first'), (1, 'second')]]
        session.add_all(rows)
        await session.commit()
        expected = [rows[1].id, rows[2].id, rows[0].id]
    path = f"/api/v1/conversations/{conversation['id']}/messages"
    assert [row['id'] for row in (await client.get(path)).json()] == expected
    assert [row['id'] for row in (await client.get(path + '?offset=1&limit=1')).json()] == expected[1:2]
    assert (await client.get(path + '?offset=100')).json() == []


@pytest.mark.parametrize('changes', [
    {'content': ''}, {'content': ' \n\t '}, {'content': 'a' * 10001},
    {'sender_id': 0}, {'sender_id': 999},
    {'sender_type': 'AI'}, {'sender_type': 'SYSTEM'}, {'message_type': 'AUDIO'},
    {'message_type': 'SYSTEM'}, {'metadata': []}, {'metadata': None},
    {'created_at': '2026-01-01T00:00:00Z'}, {'conversation_id': 999},
])
async def test_invalid_message_is_not_persisted(client, conversation, session_factory, changes):
    path = f"/api/v1/conversations/{conversation['id']}/messages"
    response = await client.post(path, json={
        'sender_id': conversation['customer_id'], 'content': 'Hello', **changes,
    })
    assert response.status_code == 422, response.text
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Message)) == 0


@pytest.mark.parametrize('method', ['post', 'get'])
async def test_missing_conversation_returns_404(client, session_factory, method):
    kwargs = {'json': {'sender_id': 1, 'content': 'Hello'}} if method == 'post' else {}
    response = await getattr(client, method)('/api/v1/conversations/999/messages', **kwargs)
    assert response.status_code == 404
    assert response.json()['code'] == 'resource_not_found'
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Message)) == 0


@pytest.mark.parametrize('query', ['offset=-1', 'limit=0', 'limit=101'])
async def test_invalid_pagination(client, conversation, query):
    response = await client.get(f"/api/v1/conversations/{conversation['id']}/messages?{query}")
    assert response.status_code == 422

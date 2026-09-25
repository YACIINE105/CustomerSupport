"""Conversation workflow through real routes, services, and repositories."""

from datetime import datetime

import pytest
from sqlalchemy import func, select

from src.models.conversation import Conversation
from src.models.customer import Customer


async def assert_database_counts(session_factory, *, customers, conversations):
    # A fresh session checks committed state, not an HTTP response or cached object.
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Customer)) == customers
        assert await session.scalar(select(func.count()).select_from(Conversation)) == conversations


@pytest.mark.parametrize("channel", ["CHAT", "VOICE", "PHONE"])
async def test_create_and_retrieve_conversation(client, session_factory, channel):
    response = await client.post("/api/v1/customers", json={"name": "Mona"})
    assert response.status_code == 201, response.text
    customer_id = response.json()["id"]

    response = await client.post(
        "/api/v1/conversations",
        json={"customer_id": customer_id, "channel": channel},
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert set(created) == {
        "id", "customer_id", "assigned_agent_id", "channel", "status", "started_at", "ended_at",
        "created_at", "updated_at",
    }
    assert isinstance(created["id"], int) and created["id"] > 0
    assert created["customer_id"] == customer_id
    assert created["channel"] == channel
    assert created["status"] == "OPEN"
    assert created["ended_at"] is None
    for field in ("started_at", "created_at", "updated_at"):
        assert isinstance(created[field], str)
        datetime.fromisoformat(created[field])
    # SQLite strips timezone information; PostgreSQL UTC behavior needs its own check.

    response = await client.get(f"/api/v1/conversations/{created['id']}")
    assert response.status_code == 200, response.text
    assert response.json() == created
    await assert_database_counts(session_factory, customers=1, conversations=1)

    async with session_factory() as session:
        stored = await session.get(Conversation, created["id"])
        assert stored.customer_id == customer_id
        assert stored.channel == channel
        assert stored.status == "OPEN"


async def test_missing_customer_does_not_persist_conversation(client, session_factory):
    response = await client.post(
        "/api/v1/conversations", json={"customer_id": 999, "channel": "CHAT"}
    )
    assert response.status_code == 404, response.text
    assert response.json() == {
        "detail": "Customer with id 999 was not found",
        "code": "resource_not_found",
    }
    await assert_database_counts(session_factory, customers=0, conversations=0)


async def test_missing_conversation_returns_not_found(client):
    response = await client.get("/api/v1/conversations/999")
    assert response.status_code == 404, response.text
    assert response.json() == {
        "detail": "Conversation with id 999 was not found",
        "code": "resource_not_found",
    }


@pytest.mark.parametrize(
    "changes, invalid_field",
    [
        ({"channel": "EMAIL"}, "channel"),
        ({"customer_id": 0}, "customer_id"),
        ({"customer_id": -1}, "customer_id"),
        ({"status": "CLOSED"}, "status"),
        ({"id": 123}, "id"),
        ({"started_at": "2026-01-01T00:00:00Z"}, "started_at"),
    ],
)
async def test_invalid_creation_does_not_persist(
    client, session_factory, changes, invalid_field
):
    response = await client.post("/api/v1/customers", json={"name": "Mona"})
    assert response.status_code == 201, response.text
    payload = {"customer_id": response.json()["id"], "channel": "CHAT", **changes}

    response = await client.post("/api/v1/conversations", json=payload)

    assert response.status_code == 422, response.text
    assert any(
        error["loc"] == ["body", invalid_field]
        for error in response.json()["detail"]
    )
    await assert_database_counts(session_factory, customers=1, conversations=0)


async def test_conversation_lifecycle_and_filters(client):
    customer = (await client.post('/api/v1/customers', json={'name': 'Mona'})).json()
    response = await client.post('/api/v1/conversations', json={'customer_id': customer['id'], 'channel': 'CHAT'})
    conv = response.json()
    path = f"/api/v1/conversations/{conv['id']}"
    assert (await client.post(path + '/close')).status_code == 409
    assert (await client.patch(path, json={'status': 'ESCALATED'})).status_code == 409
    assert (await client.patch(path, json={'status': 'WAITING'})).status_code == 200
    rows = (await client.get('/api/v1/conversations', params={'status': 'WAITING', 'customer_id': customer['id'], 'channel': 'CHAT'})).json()
    assert [row['id'] for row in rows] == [conv['id']]
    assert (await client.get('/api/v1/conversations?status=OPEN')).json() == []
    resolved = await client.post(path + '/resolve')
    assert resolved.status_code == 200
    assert resolved.json()['ended_at'] is not None
    assert (await client.post(path + '/resolve')).json()['ended_at'] == resolved.json()['ended_at']
    assert (await client.post(path + '/messages', json={'sender_id': customer['id'], 'content': 'late'})).status_code == 409
    closed = await client.post(path + '/close')
    assert closed.status_code == 200
    assert closed.json()['ended_at'] == resolved.json()['ended_at']
    assert (await client.patch(path, json={'status': 'OPEN'})).status_code == 409
    assert (await client.get('/api/v1/conversations?limit=101')).status_code == 422


async def test_assignment_eligibility_and_agent_permissions(client):
    password = 'Assignment-password-123!'
    users, agents, headers = [], [], []
    for index in range(2):
        user = (await client.post('/api/v1/auth/register', json={'email': f'assign{index}@example.com', 'password': password})).json()
        users.append(user)
        agent = (await client.post('/api/v1/agents', json={'user_id': user['id'], 'display_name': 'Agent'})).json()
        agents.append(agent)
        login = await client.post('/api/v1/auth/login', json={'email': user['email'], 'password': password})
        headers.append({'Authorization': 'Bearer ' + login.json()['access_token']})
    customer = (await client.post('/api/v1/customers', json={'name': 'Mona'})).json()
    conv = (await client.post('/api/v1/conversations', json={'customer_id': customer['id'], 'channel': 'CHAT'})).json()
    path = f"/api/v1/conversations/{conv['id']}"
    assert (await client.post(path + '/assign', json={'agent_id': agents[0]['id']})).status_code == 409
    assert (await client.post(path + '/assign', json={'agent_id': 999})).status_code == 404
    await client.patch(f"/api/v1/agents/{agents[0]['id']}/status", json={'status': 'AVAILABLE'})
    assert (await client.post(path + '/assign', headers=headers[0], json={'agent_id': agents[0]['id']})).status_code == 403
    response = await client.post(path + '/assign', json={'agent_id': agents[0]['id']})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'IN_PROGRESS'
    assert response.json()['assigned_agent_id'] == agents[0]['id']
    rows = (await client.get('/api/v1/conversations', params={'assigned_agent_id': agents[0]['id']})).json()
    assert len(rows) == 1
    assert (await client.post(path + '/resolve', headers=headers[1])).status_code == 403
    assert (await client.post(path + '/messages', headers=headers[1], json={'sender_type': 'AGENT', 'sender_id': agents[1]['id'], 'content': 'wrong owner'})).status_code == 403
    assert (await client.post(path + '/resolve', headers=headers[0])).status_code == 200
    assert (await client.post(path + '/assign', json={'agent_id': agents[0]['id']})).status_code == 409

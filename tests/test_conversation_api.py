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
        "id", "customer_id", "channel", "status", "started_at", "ended_at",
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

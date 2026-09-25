from datetime import datetime, timedelta, timezone
import pytest
from src.models.call import Call


@pytest.fixture
async def conversation(client):
    customer = (await client.post('/api/v1/customers', json={'name': 'Caller'})).json()
    return (await client.post('/api/v1/conversations', json={'customer_id': customer['id'], 'channel': 'PHONE'})).json()


async def test_call_lifecycle_duration_and_resolution_guard(client, conversation, session_factory):
    response = await client.post('/api/v1/calls', json={'conversation_id': conversation['id'], 'direction': 'INBOUND'})
    assert response.status_code == 201, response.text
    item = response.json()
    path = f"/api/v1/calls/{item['id']}"
    assert item['status'] == 'INITIATED' and item['duration_seconds'] == 0
    assert (await client.post('/api/v1/calls', json={'conversation_id': conversation['id'], 'direction': 'INBOUND'})).status_code == 409
    assert (await client.post(f"/api/v1/conversations/{conversation['id']}/resolve")).status_code == 409
    assert (await client.patch(path, json={'status': 'COMPLETED'})).status_code == 409
    assert (await client.patch(path, json={'status': 'RINGING'})).status_code == 200
    answered = await client.patch(path, json={'status': 'ANSWERED'})
    assert answered.status_code == 200 and answered.json()['answered_at'] is not None
    async with session_factory() as session:
        stored = await session.get(Call, item['id'])
        stored.answered_at = datetime.now(timezone.utc) - timedelta(seconds=45)
        await session.commit()
    ended = await client.patch(path, json={'status': 'COMPLETED', 'transcript': 'Resolved', 'recording_url': 'https://example.com/recording'})
    assert ended.status_code == 200, ended.text
    assert 45 <= ended.json()['duration_seconds'] < 60
    assert ended.json()['ended_at'] is not None
    assert (await client.patch(path, json={'status': 'COMPLETED'})).json()['ended_at'] == ended.json()['ended_at']
    assert (await client.patch(path, json={'status': 'ANSWERED'})).status_code == 409
    assert (await client.patch(path, json={'transcript': None})).json()['transcript'] is None
    assert (await client.get('/api/v1/calls?status=COMPLETED')).json()[0]['id'] == item['id']
    assert (await client.post(f"/api/v1/conversations/{conversation['id']}/resolve")).status_code == 200


@pytest.mark.parametrize('terminal', ['FAILED', 'CANCELLED', 'MISSED'])
async def test_unanswered_terminal_calls(client, conversation, terminal):
    item = (await client.post('/api/v1/calls', json={'conversation_id': conversation['id'], 'direction': 'OUTBOUND'})).json()
    path = f"/api/v1/calls/{item['id']}"
    await client.patch(path, json={'status': 'RINGING'})
    response = await client.patch(path, json={'status': terminal})
    assert response.status_code == 200
    assert response.json()['duration_seconds'] == 0
    assert response.json()['answered_at'] is None
    assert response.json()['ended_at'] is not None


async def test_call_validation_and_missing_resources(client, conversation):
    assert (await client.get('/api/v1/calls/999')).status_code == 404
    assert (await client.patch('/api/v1/calls/999', json={'status': 'ANSWERED'})).status_code == 404
    assert (await client.post('/api/v1/calls', json={'conversation_id': 999, 'direction': 'INBOUND'})).status_code == 404
    assert (await client.post('/api/v1/calls', json={'conversation_id': conversation['id'], 'direction': 'INVALID'})).status_code == 422
    assert (await client.post('/api/v1/calls', json={'conversation_id': conversation['id'], 'direction': 'INBOUND', 'duration_seconds': 50})).status_code == 422
    chat = (await client.post('/api/v1/conversations', json={'customer_id': conversation['customer_id'], 'channel': 'CHAT'})).json()
    assert (await client.post('/api/v1/calls', json={'conversation_id': chat['id'], 'direction': 'INBOUND'})).status_code == 409
    item = (await client.post('/api/v1/calls', json={'conversation_id': conversation['id'], 'direction': 'INBOUND'})).json()
    path = f"/api/v1/calls/{item['id']}"
    assert (await client.patch(path, json={'status': None})).status_code == 422
    assert (await client.patch(path, json={'recording_url': 'javascript:evil'})).status_code == 422

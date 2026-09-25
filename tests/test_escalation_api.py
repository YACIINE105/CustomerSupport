import pytest


@pytest.fixture
async def conversation(client):
    customer = (await client.post('/api/v1/customers', json={'name': 'Escalation customer'})).json()
    return (await client.post('/api/v1/conversations', json={'customer_id': customer['id'], 'channel': 'CHAT'})).json()


async def test_escalation_lifecycle_and_conversation_transaction(client, conversation):
    path = f"/api/v1/conversations/{conversation['id']}"
    response = await client.post('/api/v1/escalations', json={'conversation_id': conversation['id'], 'reason': 'Need supervisor', 'priority': 'HIGH'})
    assert response.status_code == 201, response.text
    escalation = response.json()
    escalation_path = f"/api/v1/escalations/{escalation['id']}"
    assert (await client.get(path)).json()['status'] == 'ESCALATED'
    assert (await client.post(path + '/resolve')).status_code == 409
    assert (await client.post('/api/v1/escalations', json={'conversation_id': conversation['id'], 'reason': 'Duplicate'})).status_code == 409
    assert (await client.patch(escalation_path, json={'priority': 'URGENT'})).json()['priority'] == 'URGENT'
    assert len((await client.get('/api/v1/escalations?priority=URGENT&status=OPEN')).json()) == 1
    response = await client.patch(escalation_path, json={'status': 'RESOLVED'})
    assert response.status_code == 200, response.text
    assert response.json()['resolved_at'] is not None
    assert (await client.patch(escalation_path, json={'status': 'RESOLVED'})).json()['resolved_at'] == response.json()['resolved_at']
    assert (await client.get(path)).json()['status'] == 'OPEN'
    assert (await client.patch(escalation_path, json={'priority': 'LOW'})).status_code == 409
    assert (await client.post(path + '/resolve')).status_code == 200
    assert (await client.post('/api/v1/escalations', json={'conversation_id': conversation['id'], 'reason': 'Too late'})).status_code == 409


async def test_failed_escalation_does_not_change_conversation(client, conversation):
    response = await client.post('/api/v1/escalations', json={'conversation_id': conversation['id'], 'reason': 'Help', 'assigned_agent_id': 999})
    assert response.status_code == 404
    assert (await client.get(f"/api/v1/conversations/{conversation['id']}")).json()['status'] == 'OPEN'
    assert (await client.get('/api/v1/escalations')).json() == []
    assert (await client.get('/api/v1/escalations/999')).status_code == 404
    assert (await client.patch('/api/v1/escalations/999', json={'status': 'RESOLVED'})).status_code == 404
    assert (await client.post('/api/v1/escalations', json={'conversation_id': 999, 'reason': 'Missing'})).status_code == 404


async def test_assigned_agent_can_resolve_but_not_reprioritize(client, conversation):
    password = 'Escalation-password-123!'
    user = (await client.post('/api/v1/auth/register', json={'email': 'help@example.com', 'password': password})).json()
    agent = (await client.post('/api/v1/agents', json={'user_id': user['id'], 'display_name': 'Helper'})).json()
    await client.patch(f"/api/v1/agents/{agent['id']}/status", json={'status': 'AVAILABLE'})
    item = (await client.post('/api/v1/escalations', json={'conversation_id': conversation['id'], 'reason': 'Help'})).json()
    path = f"/api/v1/escalations/{item['id']}"
    response = await client.patch(path, json={'assigned_agent_id': agent['id']})
    assert response.status_code == 200
    assert response.json()['status'] == 'ASSIGNED'
    assert (await client.get(f"/api/v1/conversations/{conversation['id']}")).json()['assigned_agent_id'] == agent['id']
    login = (await client.post('/api/v1/auth/login', json={'email': user['email'], 'password': password})).json()
    headers = {'Authorization': 'Bearer ' + login['access_token']}
    assert (await client.patch(path, headers=headers, json={'priority': 'LOW'})).status_code == 403
    assert (await client.patch(path, headers=headers, json={'status': 'RESOLVED'})).status_code == 200
    assert (await client.get(f"/api/v1/conversations/{conversation['id']}")).json()['status'] == 'IN_PROGRESS'


@pytest.mark.parametrize('changes', [{'reason': '  '}, {'priority': 'INVALID'}, {'assigned_agent_id': -1}, {'status': 'RESOLVED'}])
async def test_invalid_escalation_input(client, conversation, changes):
    assert (await client.post('/api/v1/escalations', json={'conversation_id': conversation['id'], 'reason': 'Help', **changes})).status_code == 422

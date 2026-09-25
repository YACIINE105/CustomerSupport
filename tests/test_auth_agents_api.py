from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from src.core.security import hash_password, verify_password
from src.domain.enums import UserRole
from src.models.user import User

PASSWORD = "Staff-test-password-123!"
SECRET = "test-only-secret-key-not-for-production-123456-more-entropy"


async def register(client, email="agent@example.com", role="AGENT"):
    response = await client.post('/api/v1/auth/register', json={
        'email': email, 'password': PASSWORD, 'role': role,
    })
    assert response.status_code == 201, response.text
    assert 'password' not in response.json() and 'password_hash' not in response.json()
    return response.json()


async def token(client, email):
    response = await client.post('/api/v1/auth/login', json={'email': email, 'password': PASSWORD})
    assert response.status_code == 200, response.text
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


async def profile(client, user):
    response = await client.post('/api/v1/agents', json={'user_id': user['id'], 'display_name': ' Mona ', 'department': 'Support'})
    assert response.status_code == 201, response.text
    assert response.json()['status'] == 'OFFLINE'
    assert response.json()['display_name'] == 'Mona'
    return response.json()


@pytest.mark.parametrize('method,path,body', [
    ('get', '/api/v1/customers', None), ('post', '/api/v1/customers', {'name': 'Mona'}),
    ('patch', '/api/v1/customers/1', {'name': 'Mona'}), ('delete', '/api/v1/customers/1', None),
    ('get', '/api/v1/conversations/1', None),
    ('post', '/api/v1/conversations', {'customer_id': 1, 'channel': 'CHAT'}),
    ('get', '/api/v1/conversations/1/messages', None),
    ('post', '/api/v1/conversations/1/messages', {'sender_id': 1, 'content': 'Hello'}),
    ('post', '/api/v1/auth/register', {'email': 'intruder@example.com', 'password': PASSWORD, 'role': 'ADMIN'}),
    ('get', '/api/v1/auth/me', None), ('get', '/api/v1/users', None),
    ('patch', '/api/v1/users/1', {'role': 'ADMIN'}),
    ('get', '/api/v1/agents', None), ('get', '/api/v1/agents/1', None),
    ('post', '/api/v1/agents', {'user_id': 1, 'display_name': 'Mona'}),
    ('patch', '/api/v1/agents/1/status', {'status': 'AVAILABLE'}),
])
async def test_protected_endpoints_require_bearer(anonymous_client, method, path, body):
    kwargs = {'json': body} if body is not None else {}
    response = await getattr(anonymous_client, method)(path, **kwargs)
    assert response.status_code == 401, response.text
    assert response.headers['www-authenticate'] == 'Bearer'


async def test_register_login_and_me_do_not_expose_hash(client, session_factory):
    user = await register(client, 'Agent@Example.com')
    assert user['email'] == 'agent@example.com'
    async with session_factory() as session:
        stored = await session.get(User, user['id'])
        assert stored.password_hash.startswith('$argon2id$')
        assert verify_password(PASSWORD, stored.password_hash)
    headers = await token(client, 'AGENT@EXAMPLE.COM')
    response = await client.get('/api/v1/auth/me', headers=headers)
    assert response.status_code == 200
    assert response.json() == user
    users = await client.get('/api/v1/users')
    assert all('password_hash' not in row for row in users.json())
    duplicate = await client.post('/api/v1/auth/register', json={'email': 'AGENT@example.com', 'password': PASSWORD})
    assert duplicate.status_code == 409
    async with session_factory() as session:
        assert len(list((await session.scalars(select(User).where(User.email == 'agent@example.com'))).all())) == 1


@pytest.mark.parametrize('email,password', [('admin@example.com', 'incorrect'), ('nobody@example.com', PASSWORD)])
async def test_bad_login_is_generic(client, email, password):
    response = await client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid credentials or inactive account'


@pytest.mark.parametrize('case', ['expired', 'wrong_key', 'missing_exp', 'bad_audience', 'bad_issuer', 'wrong_type', 'unknown_user', 'algorithm', 'malformed'])
async def test_invalid_tokens_rejected(client, case):
    now = datetime.now(timezone.utc)
    claims = {'sub': '1', 'iat': now, 'exp': now + timedelta(minutes=5),
              'iss': 'customer-support', 'aud': 'customer-support-api', 'token_type': 'access'}
    key, algorithm = SECRET, 'HS256'
    if case == 'expired': claims['exp'] = now - timedelta(seconds=1)
    elif case == 'wrong_key': key = 'different-secret-key-at-least-32-bytes-long'
    elif case == 'missing_exp': del claims['exp']
    elif case == 'bad_audience': claims['aud'] = 'other-api'
    elif case == 'bad_issuer': claims['iss'] = 'other-issuer'
    elif case == 'wrong_type': claims['token_type'] = 'refresh'
    elif case == 'unknown_user': claims['sub'] = '999'
    elif case == 'algorithm': algorithm = 'HS384'
    encoded = 'garbage' if case == 'malformed' else jwt.encode(claims, key, algorithm=algorithm)
    response = await client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + encoded})
    assert response.status_code == 401, response.text


async def test_agent_can_only_change_own_status(client):
    first = await register(client)
    second = await register(client, 'other@example.com')
    agent = await profile(client, first)
    other = await profile(client, second)
    headers = await token(client, first['email'])
    path = f"/api/v1/agents/{agent['id']}/status"
    for status in ['AVAILABLE', 'BUSY', 'OFFLINE']:
        response = await client.patch(path, headers=headers, json={'status': status})
        assert response.status_code == 200, response.text
        assert response.json()['status'] == status
    response = await client.patch(f"/api/v1/agents/{other['id']}/status", headers=headers, json={'status': 'BUSY'})
    assert response.status_code == 403
    assert (await client.get(f"/api/v1/agents/{other['id']}")).json()['status'] == 'OFFLINE'
    assert (await client.patch(path, json={'status': 'AVAILABLE'})).status_code == 200
    assert (await client.patch(path, json={'status': 'INVALID'})).status_code == 422
    assert (await client.patch(path, json={'status': 'BUSY', 'user_id': second['id']})).status_code == 422


async def test_profile_rules_and_missing_resources(client):
    user = await register(client)
    agent = await profile(client, user)
    assert (await client.get('/api/v1/agents')).json() == [agent]
    assert (await client.post('/api/v1/agents', json={'user_id': user['id'], 'display_name': 'Duplicate'})).status_code == 409
    assert (await client.post('/api/v1/agents', json={'user_id': 999, 'display_name': 'Missing'})).status_code == 404
    assert (await client.get('/api/v1/agents/999')).status_code == 404
    assert (await client.patch('/api/v1/agents/999/status', json={'status': 'BUSY'})).status_code == 404
    head = await register(client, 'head@example.com', 'SUPPORT_HEAD')
    assert (await client.post('/api/v1/agents', json={'user_id': head['id'], 'display_name': 'Head'})).status_code == 409
    assert (await client.patch(f"/api/v1/users/{user['id']}", json={'role': 'ADMIN'})).status_code == 409


async def test_permissions_and_current_role_are_loaded_from_database(client):
    head = await register(client, 'head@example.com', 'SUPPORT_HEAD')
    staff = await register(client)
    headers = await token(client, head['email'])
    assert (await client.get('/api/v1/users', headers=headers)).status_code == 200
    assert (await client.post('/api/v1/agents', headers=headers, json={'user_id': staff['id'], 'display_name': 'Agent'})).status_code == 201
    assert (await client.post('/api/v1/auth/register', headers=headers, json={'email': 'new@example.com', 'password': PASSWORD, 'role': 'ADMIN'})).status_code == 403
    assert (await client.patch(f"/api/v1/users/{staff['id']}", headers=headers, json={'role': 'ADMIN'})).status_code == 403
    assert (await client.patch(f"/api/v1/users/{head['id']}", json={'role': 'AGENT'})).status_code == 200
    assert (await client.get('/api/v1/users', headers=headers)).status_code == 403
    assert (await client.get('/api/v1/customers', headers=headers)).status_code == 200
    assert (await client.delete('/api/v1/customers/999', headers=headers)).status_code == 403


async def test_deactivation_revokes_token_and_sets_agent_offline(client):
    user = await register(client)
    agent = await profile(client, user)
    headers = await token(client, user['email'])
    await client.patch(f"/api/v1/agents/{agent['id']}/status", json={'status': 'AVAILABLE'})
    assert (await client.patch(f"/api/v1/users/{user['id']}", json={'is_active': False})).status_code == 200
    assert (await client.get('/api/v1/auth/me', headers=headers)).status_code == 401
    assert (await client.post('/api/v1/auth/login', json={'email': user['email'], 'password': PASSWORD})).status_code == 401
    assert (await client.get(f"/api/v1/agents/{agent['id']}")).json()['status'] == 'OFFLINE'
    assert (await client.patch(f"/api/v1/agents/{agent['id']}/status", json={'status': 'AVAILABLE'})).status_code == 409
    assert (await client.patch('/api/v1/users/1', json={'is_active': False})).status_code == 409
    assert (await client.patch('/api/v1/users/1', json={'role': 'AGENT'})).status_code == 409


async def test_agent_reply_identity_is_enforced(client):
    user = await register(client)
    agent = await profile(client, user)
    headers = await token(client, user['email'])
    customer = (await client.post('/api/v1/customers', json={'name': 'Customer'})).json()
    conversation = (await client.post('/api/v1/conversations', json={'customer_id': customer['id'], 'channel': 'CHAT'})).json()
    path = f"/api/v1/conversations/{conversation['id']}/messages"
    payload = {'sender_type': 'AGENT', 'sender_id': agent['id'], 'content': 'I can help.'}
    assert (await client.post(path, json=payload)).status_code == 403  # Admin has no agent identity.
    assert (await client.post(path, headers=headers, json={**payload, 'sender_id': 999})).status_code == 403
    response = await client.post(path, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    assert response.json()['sender_id'] == agent['id']
    assert response.json()['sender_type'] == 'AGENT'
    assert len((await client.get(path, headers=headers)).json()) == 1
    for trusted_type in ['AI', 'SYSTEM']:
        assert (await client.post(path, headers=headers, json={**payload, 'sender_type': trusted_type})).status_code == 422


@pytest.mark.parametrize('field,value', [('role', None), ('is_active', None), ('role', 'OWNER'), ('password_hash', 'x')])
async def test_invalid_user_update_rejected(client, field, value):
    assert (await client.patch('/api/v1/users/1', json={field: value})).status_code == 422


async def test_password_validation_does_not_echo_secret(client):
    secret = 'too-short'
    response = await client.post('/api/v1/auth/register', json={'email': 'weak@example.com', 'password': secret})
    assert response.status_code == 422
    assert secret not in response.text
    assert all('input' not in error for error in response.json()['detail'])


async def test_unconfigured_signing_key_fails_closed(client):
    from src.core.config import Settings, get_settings
    from src.main import app
    previous = app.dependency_overrides[get_settings]
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, jwt_secret_key='')
    try:
        response = await client.post('/api/v1/auth/login', json={'email': 'admin@example.com', 'password': 'Admin-test-password-123!'})
        assert response.status_code == 503
        assert 'access_token' not in response.json()
    finally:
        app.dependency_overrides[get_settings] = previous

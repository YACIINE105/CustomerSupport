import pytest


async def test_customer_lifecycle(client):
    response = await client.post('/api/v1/customers', json={
        'name': 'Mona', 'email': 'mona@example.com', 'phone': '+201234567890',
    })
    assert response.status_code == 201
    customer = response.json()
    assert customer['created_at'] and customer['updated_at']
    path = f"/api/v1/customers/{customer['id']}"
    assert (await client.get(path)).json() == customer

    response = await client.patch(path, json={'email': None})
    assert response.status_code == 200
    assert response.json()['email'] is None
    assert response.json()['name'] == 'Mona'
    assert response.json()['phone'] == '+201234567890'
    assert (await client.patch(path, json={})).status_code == 200

    assert (await client.patch(path, json={'name': None})).status_code == 422
    assert (await client.get(path)).json()['name'] == 'Mona'
    await client.post('/api/v1/customers', json={'name': 'Omar'})
    page = (await client.get('/api/v1/customers?offset=1&limit=1')).json()
    assert [row['name'] for row in page] == ['Omar']

    response = await client.delete(path)
    assert response.status_code == 204
    assert response.content == b''
    for method in ('get', 'patch', 'delete'):
        kwargs = {'json': {'name': 'Missing'}} if method == 'patch' else {}
        response = await getattr(client, method)(path, **kwargs)
        assert response.status_code == 404
        assert response.json()['code'] == 'resource_not_found'


@pytest.mark.parametrize('payload', [{}, {'name': ''}, {'name': 'A', 'email': 'bad'}, {'name': 'A', 'phone': '1' * 33}])
async def test_invalid_customer_is_not_persisted(client, payload):
    assert (await client.post('/api/v1/customers', json=payload)).status_code == 422
    assert (await client.get('/api/v1/customers')).json() == []


@pytest.mark.parametrize('query', ['offset=-1', 'limit=0', 'limit=101'])
async def test_invalid_pagination(client, query):
    assert (await client.get(f'/api/v1/customers?{query}')).status_code == 422

from fastapi.testclient import TestClient

from src.core.config import get_settings
from src.main import app


def test_health_and_openapi():
    with TestClient(app) as client:
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {
            'status': 'healthy',
            'app_name': get_settings().app_name,
            'app_version': get_settings().app_version,
        }
        assert '/api/v1/customers' in client.get('/openapi.json').json()['paths']

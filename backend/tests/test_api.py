from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def _write_dummy_image(path: Path, token: bytes) -> None:
    path.write_bytes(token * 800)


def _register_and_get_token(client: TestClient, email: str) -> str:
    reg = client.post('/auth/register', data={'email': email, 'password': 'password123'})
    assert reg.status_code == 200
    return reg.json()['token']


def test_register_login_and_create_report(tmp_path: Path):
    client = TestClient(app)
    token = _register_and_get_token(client, 'tester_phase2@slsu.local')

    selfie = tmp_path / 'selfie.jpg'
    accident = tmp_path / 'accident.jpg'
    _write_dummy_image(selfie, b'SELFIE')
    _write_dummy_image(accident, b'ACCIDT')

    with selfie.open('rb') as s, accident.open('rb') as a:
        resp = client.post(
            '/reports',
            headers={'Authorization': f'Bearer {token}'},
            data={
                'emergency_type': 'Fire',
                'description': 'Building fire with smoke and people trapped.',
                'latitude': '14.123',
                'longitude': '121.456',
                'device_id': 'pytest-device',
            },
            files={'selfie': ('selfie.jpg', s, 'image/jpeg'), 'accident_photo': ('accident.jpg', a, 'image/jpeg')},
        )
    assert resp.status_code == 200
    assert resp.json()['severity']['label'] in {'Low', 'Medium', 'Critical'}


def test_admin_analytics_and_model_metrics():
    client = TestClient(app)
    login = client.post('/auth/login', data={'email': 'admin@slsu.local', 'password': 'password123'})
    assert login.status_code == 200
    token = login.json()['token']

    analytics = client.get('/reports/analytics', headers={'Authorization': f'Bearer {token}'})
    assert analytics.status_code == 200
    assert 'reports_per_type' in analytics.json()

    metrics = client.get('/model/metrics', headers={'Authorization': f'Bearer {token}'})
    assert metrics.status_code == 200
    assert 'accuracy' in metrics.json()

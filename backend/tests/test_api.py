import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app

client = TestClient(app)


def test_public_monitoring_contract():
    assert client.get('/api/health').status_code == 200
    wards = client.get('/api/bhopal/wards').json()['wards']
    assert len(wards) == 10
    assert client.get('/api/ward/BPL_W001/weather').status_code == 200
    assert len(client.get('/api/ward/BPL_W001/thermal-indices').json()['thermal_indices']) == 5
    assert len(client.get('/api/ward/BPL_W001/weather').json()['weather_data']) == 40
    assert len(client.get('/api/ward/BPL_W001/forecast').json()['forecast']) == 5
    assert client.get('/api/ward/BPL_W001/alert-status').json()['current_alert_level'] in {'Green', 'Yellow', 'Orange', 'Red'}


def test_authentication_and_role_guards():
    assert client.get('/api/admin/municipality-suggestions?ward_id=BPL_W001').status_code == 401
    login = client.post('/api/auth/login', json={'email': 'admin.bhopal@taapkavach.gov.in', 'password': 'demo-admin'})
    assert login.status_code == 200
    token = login.json()['access_token']
    assert client.get('/api/admin/municipality-suggestions?ward_id=BPL_W001', headers={'Authorization': f'Bearer {token}'}).status_code == 200
    assert client.get('/api/healthcare/hospital-readiness?ward_id=BPL_W001', headers={'Authorization': f'Bearer {token}'}).status_code == 403


def test_validation_errors_are_useful():
    assert client.get('/api/ward/UNKNOWN/weather').status_code == 404
    response = client.post('/api/thermal/calculate', json={'temperature': 100, 'humidity': 40, 'wind_speed': 10, 'atmospheric_pressure': 1000, 'uv_index': 8, 'solar_radiation': 500})
    assert response.status_code == 422


def test_context_aware_chat_contract():
    response = client.post('/api/chat', json={'question': 'Why is Bhel Nagar at risk?', 'ward_id': 'BPL_W007'})
    assert response.status_code == 200
    body = response.json()
    assert body['provider'] == 'local-rule-engine'
    assert body['ward_name'] == 'Bhel Nagar'
    assert body['alert_level'] == 'Red'
    assert 'Bhel Nagar' in body['answer']

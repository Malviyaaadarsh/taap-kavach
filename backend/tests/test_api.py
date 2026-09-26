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
    # Test forecast endpoint
    forecast_data = client.get('/api/ward/BPL_W001/forecast?days_ahead=4').json()
    assert len(forecast_data['forecast']) == 4
    assert 'alert_timeline' in forecast_data
    assert 'model_comparison' in forecast_data
    assert client.get('/api/ward/BPL_W001/alert-status').json()['current_alert_level'] in {'Green', 'Yellow', 'Orange', 'Red'}


def test_v2_geographic_hierarchy():
    states = client.get('/api/locations/states').json()['states']
    assert len(states) >= 1
    assert states[0]['id'] == 'MP'

    districts = client.get('/api/locations/districts?state_id=MP').json()['districts']
    assert any(d['id'] == 'bhopal' for d in districts)
    assert any(d['id'] == 'indore' for d in districts)

    cities = client.get('/api/locations/cities?district_id=bhopal').json()['cities']
    assert any(c['id'] == 'bhopal_bmc' for c in cities)

    wards = client.get('/api/locations/wards?city_id=bhopal_bmc').json()['wards']
    assert len(wards) == 10


def test_v2_city_overview_and_risk_map():
    summary = client.get('/api/city/bhopal_bmc/summary').json()
    assert summary['status_summary']['total_monitored_wards'] == 10
    assert 'alert_counts' in summary['status_summary']
    assert len(summary['highest_risk_wards']) <= 4
    assert len(summary['city_forecast_trend']) == 5

    risk_map = client.get('/api/city/bhopal_bmc/risk-map').json()
    assert risk_map['type'] == 'FeatureCollection'
    assert len(risk_map['features']) == 10


def test_v2_ward_intelligence():
    # Current condition with HTSI and risk drivers
    current = client.get('/api/ward/BPL_W003/current').json()
    assert current['ward_name'] == 'Habibganj'
    assert 'htsi' in current['thermal_metrics']
    assert 0 <= current['thermal_metrics']['htsi'] <= 100
    assert 'risk_drivers' in current
    assert 'elevated_contributors' in current['risk_drivers']

    # 10-day history
    history = client.get('/api/ward/BPL_W003/history?days_back=10').json()
    assert len(history['history']) == 10
    assert any(h['data_status'] == 'OBSERVED' for h in history['history'])
    assert any(h['data_status'] == 'HISTORICAL_BASELINE' for h in history['history'])

    # 4-day forecast with models
    fc = client.get('/api/ward/BPL_W003/forecast?days_ahead=4').json()
    assert len(fc['forecast']) == 4
    assert 'xgboost' in fc['forecast'][0]['models']
    assert 'sarima' in fc['forecast'][0]['models']

    # Risk & planning estimates
    risk = client.get('/api/ward/BPL_W003/risk').json()
    assert 'demographics' in risk
    assert 'planning_estimates' in risk
    assert 'population_exposed' in risk['planning_estimates']
    assert 'health_impact_risk' in risk
    assert 'score' in risk['health_impact_risk']

    # Recommendations
    recs = client.get('/api/ward/BPL_W003/recommendations').json()
    assert len(recs['municipal_actions']) > 0
    assert len(recs['healthcare_actions']) > 0
    assert len(recs['readiness_checklist']) >= 6
    assert 'citizen_guidance' in recs

    # Seasonal windows
    windows = client.get('/api/ward/BPL_W003/seasonal-windows').json()
    assert '2026_current_window' in windows['seasonal_comparison']
    assert '2025_same_window' in windows['seasonal_comparison']
    assert '2024_same_window' in windows['seasonal_comparison']


def test_v2_admin_and_healthcare_workspaces():
    admin_ov = client.get('/api/admin/overview').json()
    assert 'situation_summary' in admin_ov
    assert len(admin_ov['priority_wards_table']) == 10

    admin_act = client.get('/api/admin/actions?ward_id=BPL_W003').json()
    assert 'municipal_actions' in admin_act
    assert 'simulated_sms_broadcast' in admin_act

    health_ov = client.get('/api/healthcare/overview').json()
    assert health_ov['total_monitored_wards'] == 10

    health_ready = client.get('/api/healthcare/readiness?ward_id=BPL_W003').json()
    assert len(health_ready['readiness_checklist']) >= 6
    assert len(health_ready['healthcare_facilities']) > 0


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

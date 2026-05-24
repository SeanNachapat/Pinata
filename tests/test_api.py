import pytest
from fastapi.testclient import TestClient
from dummio.devices import IndustrialMotor
from dummio.server import Server

@pytest.fixture
def test_client():
    motor = IndustrialMotor()
    # We pass mqtt_host as dummy to avoid trying to connect to a real broker in simple tests
    server = Server(device=motor, mqtt_host="dummy")
    return TestClient(server.app)

def test_inject_anomaly(test_client):
    response = test_client.post(
        "/api/inject",
        json={"anomaly_type": "bearing_wear", "duration_seconds": 60, "intensity": 2.0}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_clear_anomaly(test_client):
    response = test_client.post("/api/clear")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

from fastapi.testclient import TestClient

from scalper.main import app


def test_health_exposes_paper_sources() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["executionMode"] == "PAPER"
    assert body["marketDataProvider"] == "PUBLIC"
    assert body["executionBroker"] == "INTERNAL_PAPER"


def test_public_config_never_exposes_credentials() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/meta/config")
    body = response.json()
    serialized = str(body).lower()
    assert "secret" not in serialized
    assert "token" not in serialized
    assert body["strategyBuyingPowerFraction"] == "0.50"

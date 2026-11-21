from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_ok_when_database_reachable():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

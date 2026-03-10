def test_app_imports():
    from app.main import app
    assert app is not None


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_response_shape(client):
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "checks" in data


def test_health_service_name(client):
    response = client.get("/health")
    data = response.json()
    assert data["service"] == "transcriber"


def test_health_checks_contains_database(client):
    response = client.get("/health")
    data = response.json()
    assert "database" in data["checks"]


def test_health_checks_contains_whisper_model(client):
    response = client.get("/health")
    data = response.json()
    assert "whisper_model" in data["checks"]

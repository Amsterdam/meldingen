from fastapi.testclient import TestClient

from main import app


def test_create_melding(apply_migrations: None) -> None:
    client = TestClient(app)

    response = client.post(app.url_path_for("melding:create"), json={"text": "This is a test melding."})

    assert response.status_code == 200

    data = response.json()
    assert data.get("id") == 1
    assert data.get("text") == "This is a test melding."

from fastapi.testclient import TestClient

from main import app


def test_create_melding() -> None:
    client = TestClient(app)

    response = client.post("/melding", json={"text": "This is a test melding."})

    assert response.status_code == 200

    data = response.json()
    assert data.get("id") == 1
    assert data.get("text") == "This is a test melding."

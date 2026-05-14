from fastapi.testclient import TestClient
from src.app import add, app

client = TestClient(app)


def test_add():
    assert add(2, 3) == 5


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "OK",
        "message": "FastAPI service is running",
    }


def test_add_endpoint():
    response = client.get("/add?a=5&b=7")
    assert response.status_code == 200
    assert response.json() == {"result": 12}

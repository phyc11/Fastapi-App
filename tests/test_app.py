from fastapi.testclient import TestClient
from src.app import add, app, average, divide, modulo, multiply, subtract

client = TestClient(app)


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(5, 3) == 2


def test_multiply():
    assert multiply(5, 3) == 15


def test_divide():
    assert divide(6, 3) == 2.0


def test_modulo():
    assert modulo(7, 3) == 1


def test_average():
    assert average(5, 8) == 6.5


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


def test_subtract_endpoint():
    response = client.get("/subtract?a=7&b=5")
    assert response.status_code == 200
    assert response.json() == {"result": 2}


def test_multiply_endpoint():
    response = client.get("/multiply?a=6&b=7")
    assert response.status_code == 200
    assert response.json() == {"result": 42}


def test_divide_endpoint():
    response = client.get("/divide?a=8&b=4")
    assert response.status_code == 200
    assert response.json() == {"result": 2.0}


def test_modulo_endpoint():
    response = client.get("/modulo?a=7&b=3")
    assert response.status_code == 200
    assert response.json() == {"result": 1}


def test_average_endpoint():
    response = client.get("/average?a=5&b=8")
    assert response.status_code == 200
    assert response.json() == {"result": 6.5}

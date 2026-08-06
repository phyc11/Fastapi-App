import pytest
from fastapi.testclient import TestClient

from src.app import add, app, average, divide, fibonacci, greet, increment, is_palindrome, mean, median, modulo, multiply, power, reverse_string, stddev, subtract

client = TestClient(app)


def test_add():
    assert add(2, 3) == 5


def test_increment():
    assert increment(2) == 3


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


@pytest.mark.parametrize(("n", "expected"), [(0, 0), (1, 1), (10, 55)])
def test_fibonacci(n, expected):
    assert fibonacci(n) == expected


def test_fibonacci_rejects_negative_n():
    with pytest.raises(ValueError, match="n must be non-negative"):
        fibonacci(-1)

def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_median_for_odd_and_even_lengths():
    assert median([3, 1, 2]) == 2
    assert median([4, 1, 3, 2]) == 2.5


def test_stddev():
    assert stddev([1, 2, 3]) == pytest.approx((2 / 3) ** 0.5)


@pytest.mark.parametrize("function", [mean, median, stddev])
def test_statistics_functions_reject_empty_lists(function):
    with pytest.raises(ValueError, match="numbers must not be empty"):
        function([])

def test_reverse_string():
    assert reverse_string("FastAPI") == "IPAtsaF"


def test_is_palindrome_calls_reverse_string(monkeypatch):
    calls = []

    def tracked_reverse_string(s):
        calls.append(s)
        return s[::-1]

    monkeypatch.setattr("src.app.reverse_string", tracked_reverse_string)
    assert is_palindrome("Never odd or even") is True
    assert calls == ["neveroddoreven"]


def test_is_palindrome_rejects_non_palindrome():
    assert is_palindrome("Fast API") is False

def test_greet():
    assert greet("Alice") == "Hello, Alice!"


def test_power():
    assert power(2, 3) == 8


def test_power_rejects_negative_exponent():
    with pytest.raises(ValueError, match="Exponent must be non-negative"):
        power(2, -1)


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


def test_increment_endpoint():
    response = client.get("/increment?a=5")
    assert response.status_code == 200
    assert response.json() == {"result": 6}


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


def test_fibonacci_endpoint():
    response = client.get("/fibonacci?n=10")
    assert response.status_code == 200
    assert response.json() == {"result": 55}


def test_fibonacci_endpoint_rejects_negative_n():
    response = client.get("/fibonacci?n=-1")
    assert response.status_code == 400
    assert response.json() == {"detail": "n must be non-negative"}

def test_stats_endpoint():
    response = client.get("/stats?numbers=1,2,3")
    assert response.status_code == 200
    assert response.json() == {
        "mean": 2.0,
        "median": 2.0,
        "stddev": pytest.approx((2 / 3) ** 0.5),
    }


@pytest.mark.parametrize("numbers", ["", "1,two,3", "1,,3"])
def test_stats_endpoint_rejects_empty_or_invalid_numbers(numbers):
    response = client.get("/stats", params={"numbers": numbers})
    assert response.status_code == 400
    assert response.json()["detail"]

def test_palindrome_endpoint():
    response = client.get("/palindrome", params={"text": "Never odd or even"})
    assert response.status_code == 200
    assert response.json() == {"is_palindrome": True}


def test_palindrome_endpoint_for_non_palindrome():
    response = client.get("/palindrome", params={"text": "FastAPI"})
    assert response.status_code == 200
    assert response.json() == {"is_palindrome": False}

def test_greet_endpoint():
    response = client.get("/greet?name=Alice")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Alice!"}


def test_power_endpoint():
    response = client.get("/power?a=2&b=4")
    assert response.status_code == 200
    assert response.json() == {"result": 16}


def test_power_endpoint_rejects_negative_exponent():
    response = client.get("/power?a=2&b=-1")
    assert response.status_code == 400
    assert response.json() == {"detail": "Exponent must be non-negative"}

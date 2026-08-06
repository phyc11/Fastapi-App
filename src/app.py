import os
from math import isfinite, sqrt
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI()


def add(a: int, b: int) -> int:
    return a + b


def increment(a: int) -> int:
    return a + 1


def subtract(a: int, b: int) -> int:
    return a - b


def multiply(a: int, b: int) -> int:
    return a * b


def divide(a: int, b: int) -> float:
    return a / b


def modulo(a: int, b: int) -> int:
    return a % b


def average(a: int, b: int) -> float:
    return add(a, b) / 2


def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")

    current, following = 0, 1
    for _ in range(n):
        current, following = following, current + following
    return current

def mean(numbers: list[int | float]) -> float:
    if not numbers:
        raise ValueError("numbers must not be empty")
    return sum(numbers) / len(numbers)


def median(numbers: list[int | float]) -> int | float:
    if not numbers:
        raise ValueError("numbers must not be empty")

    sorted_numbers = sorted(numbers)
    midpoint = len(sorted_numbers) // 2
    if len(sorted_numbers) % 2:
        return sorted_numbers[midpoint]
    return (sorted_numbers[midpoint - 1] + sorted_numbers[midpoint]) / 2


def stddev(numbers: list[int | float]) -> float:
    average_value = mean(numbers)
    variance = sum((number - average_value) ** 2 for number in numbers) / len(numbers)
    return sqrt(variance)

def greet(name: str) -> str:
    return f"Hello, {name}!"


def power(a: int, b: int) -> int:
    if b < 0:
        raise ValueError("Exponent must be non-negative")
    return a ** b


@app.get("/")
def read_root():
    return {"status": "OK", "message": "FastAPI service is running"}


@app.get("/add")
def add_endpoint(a: int = 0, b: int = 0):
    return {"result": add(a, b)}


@app.get("/increment")
def increment_endpoint(a: int = 0):
    return {"result": increment(a)}


@app.get("/subtract")
def subtract_endpoint(a: int = 0, b: int = 0):
    return {"result": subtract(a, b)}


@app.get("/multiply")
def multiply_endpoint(a: int = 0, b: int = 0):
    return {"result": multiply(a, b)}


@app.get("/divide")
def divide_endpoint(a: int = 0, b: int = 0):
    return {"result": divide(a, b)}


@app.get("/modulo")
def modulo_endpoint(a: int = 0, b: int = 0):
    return {"result": modulo(a, b)}


@app.get("/average")
def average_endpoint(a: int = 0, b: int = 0):
    return {"result": average(a, b)}


@app.get("/fibonacci")
def fibonacci_endpoint(n: int = 0):
    try:
        return {"result": fibonacci(n)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/stats")
def stats_endpoint(numbers: str = ""):
    try:
        if not numbers.strip():
            raise ValueError("numbers must not be empty")
        parsed_numbers = [float(value.strip()) for value in numbers.split(",")]
        if not all(isfinite(number) for number in parsed_numbers):
            raise ValueError("numbers must contain only finite numeric values")
        return {
            "mean": mean(parsed_numbers),
            "median": median(parsed_numbers),
            "stddev": stddev(parsed_numbers),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/greet")
def greet_endpoint(name: str):
    return {"message": greet(name)}


@app.get("/power")
def power_endpoint(a: int = 0, b: int = 0):
    try:
        return {"result": power(a, b)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("src.app:app", host=host, port=port, reload=False)

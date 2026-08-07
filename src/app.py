import os
from math import isfinite, isqrt, sqrt
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

def gcd(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def lcm(a: int, b: int) -> int:
    divisor = gcd(a, b)
    if divisor == 0:
        return 0
    return abs(a * b) // divisor

def is_prime(n: int) -> bool:
    if n < 2:
        raise ValueError("n must be at least 2")
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    return all(n % divisor != 0 for divisor in range(3, isqrt(n) + 1, 2))

def reverse_string(s: str) -> str:
    return s[::-1]


def is_palindrome(s: str) -> bool:
    normalized = s.lower().replace(" ", "")
    return normalized == reverse_string(normalized)

def celsius_to_fahrenheit(c: int | float) -> float:
    return c * 9 / 5 + 32


def fahrenheit_to_celsius(f: int | float) -> float:
    return (f - 32) * 5 / 9

def sort_numbers(numbers: list[int | float]) -> list[int | float]:
    result = numbers.copy()
    for index in range(1, len(result)):
        current = result[index]
        position = index - 1
        while position >= 0 and result[position] > current:
            result[position + 1] = result[position]
            position -= 1
        result[position + 1] = current
    return result

def clamp(
    value: int | float,
    min_value: int | float,
    max_value: int | float,
) -> int | float:
    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value

def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")

    result = 1
    for factor in range(2, n + 1):
        result *= factor
    return result

def reverse_list(items: list) -> list:
    result = []
    for index in range(len(items) - 1, -1, -1):
        result.append(items[index])
    return result

def word_count(text: str) -> int:
    return len(text.split())

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

@app.get("/lcm")
def lcm_endpoint(a: int = 0, b: int = 0):
    return {"result": lcm(a, b)}

@app.get("/is-prime")
def is_prime_endpoint(n: int = 0):
    try:
        return {"is_prime": is_prime(n)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/palindrome")
def palindrome_endpoint(text: str):
    return {"is_palindrome": is_palindrome(text)}

@app.get("/convert-temp")
def convert_temp_endpoint(value: float, unit: str):
    if unit == "C":
        return {"result": celsius_to_fahrenheit(value)}
    if unit == "F":
        return {"result": fahrenheit_to_celsius(value)}
    raise HTTPException(status_code=400, detail="unit must be 'C' or 'F'")

@app.get("/sort")
def sort_endpoint(numbers: str = ""):
    try:
        if not numbers.strip():
            raise ValueError("numbers must not be empty")
        parsed_numbers = [float(value.strip()) for value in numbers.split(",")]
        if not all(isfinite(number) for number in parsed_numbers):
            raise ValueError("numbers must contain only finite numeric values")
        return {"result": sort_numbers(parsed_numbers)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/clamp")
def clamp_endpoint(value: float, min_value: float, max_value: float):
    try:
        return {"result": clamp(value, min_value, max_value)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/factorial")
def factorial_endpoint(n: int = 0):
    try:
        return {"result": factorial(n)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/reverse-list")
def reverse_list_endpoint(items: str = ""):
    parsed_items = [] if not items else [item.strip() for item in items.split(",")]
    return {"result": reverse_list(parsed_items)}

@app.get("/word-count")
def word_count_endpoint(text: str = ""):
    return {"result": word_count(text)}

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

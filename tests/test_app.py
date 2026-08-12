import pytest
from fastapi.testclient import TestClient

from src.app import (
    add,
    app,
    average,
    calculate_bmi,
    clamp,
    celsius_to_fahrenheit,
    classify_bmi,
    compound_interest,
    count_vowels,
    divide,
    factorial,
    fahrenheit_to_celsius,
    fibonacci,
    gcd,
    greet,
    increment,
    is_anagram,
    is_leap_year,
    is_palindrome,
    is_prime,
    lcm,
    mean,
    median,
    modulo,
    multiply,
    power,
    reverse_list,
    reverse_string,
    sort_numbers,
    stddev,
    subtract,
    to_binary,
    word_count,
)

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

@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(12, 18, 6), (18, 12, 6), (-12, 18, 6), (0, 5, 5), (0, 0, 0)],
)
def test_gcd(a, b, expected):
    assert gcd(a, b) == expected


def test_lcm_calls_gcd(monkeypatch):
    calls = []

    def tracked_gcd(a, b):
        calls.append((a, b))
        return 2

    monkeypatch.setattr("src.app.gcd", tracked_gcd)
    assert lcm(4, 6) == 12
    assert calls == [(4, 6)]


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(4, 6, 12), (-4, 6, 12), (0, 6, 0), (0, 0, 0)],
)
def test_lcm(a, b, expected):
    assert lcm(a, b) == expected

@pytest.mark.parametrize("n", [2, 3, 5, 11, 97])
def test_is_prime_for_prime_numbers(n):
    assert is_prime(n) is True


@pytest.mark.parametrize("n", [4, 9, 25, 100])
def test_is_prime_for_composite_numbers(n):
    assert is_prime(n) is False


@pytest.mark.parametrize("n", [-1, 0, 1])
def test_is_prime_rejects_numbers_less_than_two(n):
    with pytest.raises(ValueError, match="n must be at least 2"):
        is_prime(n)

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

@pytest.mark.parametrize(("celsius", "expected"), [(0, 32), (100, 212), (-40, -40)])
def test_celsius_to_fahrenheit(celsius, expected):
    assert celsius_to_fahrenheit(celsius) == pytest.approx(expected)


@pytest.mark.parametrize(("fahrenheit", "expected"), [(32, 0), (212, 100), (-40, -40)])
def test_fahrenheit_to_celsius(fahrenheit, expected):
    assert fahrenheit_to_celsius(fahrenheit) == pytest.approx(expected)

@pytest.mark.parametrize(
    ("numbers", "expected"),
    [
        ([3, 1, 2], [1, 2, 3]),
        ([4, -1, 4, 0], [-1, 0, 4, 4]),
        ([], []),
        ([1], [1]),
    ],
)
def test_sort_numbers(numbers, expected):
    assert sort_numbers(numbers) == expected


def test_sort_numbers_does_not_mutate_input():
    numbers = [3, 1, 2]
    sort_numbers(numbers)
    assert numbers == [3, 1, 2]

@pytest.mark.parametrize(
    ("value", "min_value", "max_value", "expected"),
    [
        (-1, 0, 10, 0),
        (11, 0, 10, 10),
        (5, 0, 10, 5),
        (0, 0, 10, 0),
        (10, 0, 10, 10),
    ],
)
def test_clamp(value, min_value, max_value, expected):
    assert clamp(value, min_value, max_value) == expected


def test_clamp_rejects_invalid_range():
    with pytest.raises(
        ValueError, match="min_value must be less than or equal to max_value"
    ):
        clamp(5, 10, 0)

@pytest.mark.parametrize(("n", "expected"), [(0, 1), (1, 1), (5, 120), (10, 3628800)])
def test_factorial(n, expected):
    assert factorial(n) == expected


def test_factorial_rejects_negative_n():
    with pytest.raises(ValueError, match="n must be non-negative"):
        factorial(-1)

@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([1, 2, 3], [3, 2, 1]),
        (["a", "b", "c"], ["c", "b", "a"]),
        ([], []),
        ([1], [1]),
    ],
)
def test_reverse_list(items, expected):
    assert reverse_list(items) == expected


def test_reverse_list_does_not_mutate_input():
    items = [1, 2, 3]
    reverse_list(items)
    assert items == [1, 2, 3]

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hello world", 2),
        ("  hello   world  ", 2),
        ("hello\tworld\nfrom FastAPI", 4),
        ("", 0),
        ("   \t\n", 0),
    ],
)
def test_word_count(text, expected):
    assert word_count(text) == expected

@pytest.mark.parametrize(
    ("year", "expected"),
    [(2000, True), (2024, True), (1900, False), (2023, False), (2100, False)],
)
def test_is_leap_year(year, expected):
    assert is_leap_year(year) is expected

@pytest.mark.parametrize(
    ("n", "expected"),
    [(0, "0"), (1, "1"), (2, "10"), (10, "1010"), (255, "11111111")],
)
def test_to_binary(n, expected):
    assert to_binary(n) == expected


def test_to_binary_rejects_negative_n():
    with pytest.raises(ValueError, match="n must be non-negative"):
        to_binary(-1)

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello World", 3),
        ("AEIOUaeiou", 10),
        ("rhythms", 0),
        ("", 0),
    ],
)
def test_count_vowels(text, expected):
    assert count_vowels(text) == expected

@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("listen", "silent", True),
        ("Dormitory", "Dirty room", True),
        ("A gentleman", "Elegant man", True),
        ("aab", "abb", False),
        ("hello", "world", False),
        ("abc", "ab", False),
        ("", "   ", True),
    ],
)
def test_is_anagram(a, b, expected):
    assert is_anagram(a, b) is expected

@pytest.mark.parametrize(
    ("principal", "rate", "years", "expected"),
    [
        (1000, 0.05, 2, 1102.5),
        (1000, 0.05, 0, 1000),
        (0, 0.10, 10, 0),
        (100, -0.10, 2, 81),
    ],
)
def test_compound_interest(principal, rate, years, expected):
    assert compound_interest(principal, rate, years) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("principal", "rate", "years", "message"),
    [
        (-1, 0.05, 2, "principal must be non-negative"),
        (1000, 0.05, -1, "years must be non-negative"),
    ],
)
def test_compound_interest_rejects_negative_input(
    principal, rate, years, message
):
    with pytest.raises(ValueError, match=message):
        compound_interest(principal, rate, years)

def test_calculate_bmi():
    assert calculate_bmi(70, 1.75) == pytest.approx(70 / 1.75**2)


@pytest.mark.parametrize(
    ("weight", "height", "message"),
    [
        (0, 1.75, "weight must be a positive finite number"),
        (-1, 1.75, "weight must be a positive finite number"),
        (70, 0, "height must be a positive finite number"),
        (70, -1, "height must be a positive finite number"),
    ],
)
def test_calculate_bmi_rejects_invalid_input(weight, height, message):
    with pytest.raises(ValueError, match=message):
        calculate_bmi(weight, height)


@pytest.mark.parametrize(
    ("bmi_value", "expected"),
    [
        (18.49, "underweight"),
        (18.5, "normal"),
        (24.99, "normal"),
        (25, "overweight"),
        (29.99, "overweight"),
        (30, "obese"),
    ],
)
def test_classify_bmi(bmi_value, expected):
    assert classify_bmi(bmi_value) == expected

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

def test_lcm_endpoint():
    response = client.get("/lcm?a=4&b=6")
    assert response.status_code == 200
    assert response.json() == {"result": 12}


def test_lcm_endpoint_calls_lcm(monkeypatch):
    calls = []

    def tracked_lcm(a, b):
        calls.append((a, b))
        return 99

    monkeypatch.setattr("src.app.lcm", tracked_lcm)
    response = client.get("/lcm?a=8&b=12")
    assert response.status_code == 200
    assert response.json() == {"result": 99}
    assert calls == [(8, 12)]

@pytest.mark.parametrize(("n", "expected"), [(29, True), (49, False)])
def test_is_prime_endpoint(n, expected):
    response = client.get("/is-prime", params={"n": n})
    assert response.status_code == 200
    assert response.json() == {"is_prime": expected}


def test_is_prime_endpoint_rejects_numbers_less_than_two():
    response = client.get("/is-prime?n=1")
    assert response.status_code == 400
    assert response.json() == {"detail": "n must be at least 2"}

def test_palindrome_endpoint():
    response = client.get("/palindrome", params={"text": "Never odd or even"})
    assert response.status_code == 200
    assert response.json() == {"is_palindrome": True}


def test_palindrome_endpoint_for_non_palindrome():
    response = client.get("/palindrome", params={"text": "FastAPI"})
    assert response.status_code == 200
    assert response.json() == {"is_palindrome": False}

def test_convert_temp_endpoint_calls_celsius_helper(monkeypatch):
    calls = []

    def tracked_conversion(value):
        calls.append(value)
        return 77.0

    monkeypatch.setattr("src.app.celsius_to_fahrenheit", tracked_conversion)
    response = client.get("/convert-temp?value=25&unit=C")
    assert response.status_code == 200
    assert response.json() == {"result": 77.0}
    assert calls == [25.0]


def test_convert_temp_endpoint_calls_fahrenheit_helper(monkeypatch):
    calls = []

    def tracked_conversion(value):
        calls.append(value)
        return 12.5

    monkeypatch.setattr("src.app.fahrenheit_to_celsius", tracked_conversion)
    response = client.get("/convert-temp?value=50&unit=F")
    assert response.status_code == 200
    assert response.json() == {"result": 12.5}
    assert calls == [50.0]


def test_convert_temp_endpoint_rejects_invalid_unit():
    response = client.get("/convert-temp?value=25&unit=K")
    assert response.status_code == 400
    assert response.json() == {"detail": "unit must be 'C' or 'F'"}

def test_sort_endpoint():
    response = client.get("/sort?numbers=3,1,2")
    assert response.status_code == 200
    assert response.json() == {"result": [1.0, 2.0, 3.0]}


def test_sort_endpoint_calls_sort_numbers(monkeypatch):
    calls = []

    def tracked_sort_numbers(numbers):
        calls.append(numbers)
        return [99.0]

    monkeypatch.setattr("src.app.sort_numbers", tracked_sort_numbers)
    response = client.get("/sort?numbers=3,1,2")
    assert response.status_code == 200
    assert response.json() == {"result": [99.0]}
    assert calls == [[3.0, 1.0, 2.0]]


@pytest.mark.parametrize("numbers", ["", "3,two,1", "3,,1"])
def test_sort_endpoint_rejects_empty_or_invalid_numbers(numbers):
    response = client.get("/sort", params={"numbers": numbers})
    assert response.status_code == 400
    assert response.json()["detail"]

@pytest.mark.parametrize(
    ("value", "expected"), [(-1, 0.0), (5, 5.0), (11, 10.0)]
)
def test_clamp_endpoint(value, expected):
    response = client.get(
        "/clamp", params={"value": value, "min_value": 0, "max_value": 10}
    )
    assert response.status_code == 200
    assert response.json() == {"result": expected}


def test_clamp_endpoint_calls_clamp(monkeypatch):
    calls = []

    def tracked_clamp(value, min_value, max_value):
        calls.append((value, min_value, max_value))
        return 99.0

    monkeypatch.setattr("src.app.clamp", tracked_clamp)
    response = client.get("/clamp?value=5&min_value=0&max_value=10")
    assert response.status_code == 200
    assert response.json() == {"result": 99.0}
    assert calls == [(5.0, 0.0, 10.0)]


def test_clamp_endpoint_rejects_invalid_range():
    response = client.get("/clamp?value=5&min_value=10&max_value=0")
    assert response.status_code == 400
    assert response.json() == {
        "detail": "min_value must be less than or equal to max_value"
    }

@pytest.mark.parametrize(("n", "expected"), [(0, 1), (5, 120)])
def test_factorial_endpoint(n, expected):
    response = client.get("/factorial", params={"n": n})
    assert response.status_code == 200
    assert response.json() == {"result": expected}


def test_factorial_endpoint_calls_factorial(monkeypatch):
    calls = []

    def tracked_factorial(n):
        calls.append(n)
        return 99

    monkeypatch.setattr("src.app.factorial", tracked_factorial)
    response = client.get("/factorial?n=5")
    assert response.status_code == 200
    assert response.json() == {"result": 99}
    assert calls == [5]


def test_factorial_endpoint_rejects_negative_n():
    response = client.get("/factorial?n=-1")
    assert response.status_code == 400
    assert response.json() == {"detail": "n must be non-negative"}

def test_reverse_list_endpoint():
    response = client.get("/reverse-list", params={"items": "a,b,c"})
    assert response.status_code == 200
    assert response.json() == {"result": ["c", "b", "a"]}


def test_reverse_list_endpoint_calls_reverse_list(monkeypatch):
    calls = []

    def tracked_reverse_list(items):
        calls.append(items)
        return ["tracked"]

    monkeypatch.setattr("src.app.reverse_list", tracked_reverse_list)
    response = client.get("/reverse-list", params={"items": "a, b, c"})
    assert response.status_code == 200
    assert response.json() == {"result": ["tracked"]}
    assert calls == [["a", "b", "c"]]


def test_reverse_list_endpoint_accepts_empty_items():
    response = client.get("/reverse-list?items=")
    assert response.status_code == 200
    assert response.json() == {"result": []}

def test_word_count_endpoint():
    response = client.get("/word-count", params={"text": "hello world from FastAPI"})
    assert response.status_code == 200
    assert response.json() == {"result": 4}


def test_word_count_endpoint_calls_word_count(monkeypatch):
    calls = []

    def tracked_word_count(text):
        calls.append(text)
        return 99

    monkeypatch.setattr("src.app.word_count", tracked_word_count)
    response = client.get("/word-count", params={"text": "hello world"})
    assert response.status_code == 200
    assert response.json() == {"result": 99}
    assert calls == ["hello world"]


@pytest.mark.parametrize("text", ["", "   "])
def test_word_count_endpoint_accepts_empty_or_whitespace_text(text):
    response = client.get("/word-count", params={"text": text})
    assert response.status_code == 200
    assert response.json() == {"result": 0}

@pytest.mark.parametrize(
    ("year", "expected"),
    [(2000, True), (2024, True), (1900, False), (2023, False)],
)
def test_is_leap_year_endpoint(year, expected):
    response = client.get("/is-leap-year", params={"year": year})
    assert response.status_code == 200
    assert response.json() == {"is_leap_year": expected}


def test_is_leap_year_endpoint_calls_helper(monkeypatch):
    calls = []

    def tracked_is_leap_year(year):
        calls.append(year)
        return True

    monkeypatch.setattr("src.app.is_leap_year", tracked_is_leap_year)
    response = client.get("/is-leap-year?year=2023")
    assert response.status_code == 200
    assert response.json() == {"is_leap_year": True}
    assert calls == [2023]

@pytest.mark.parametrize(("n", "expected"), [(0, "0"), (10, "1010")])
def test_to_binary_endpoint(n, expected):
    response = client.get("/to-binary", params={"n": n})
    assert response.status_code == 200
    assert response.json() == {"result": expected}


def test_to_binary_endpoint_calls_helper(monkeypatch):
    calls = []

    def tracked_to_binary(n):
        calls.append(n)
        return "tracked"

    monkeypatch.setattr("src.app.to_binary", tracked_to_binary)
    response = client.get("/to-binary?n=10")
    assert response.status_code == 200
    assert response.json() == {"result": "tracked"}
    assert calls == [10]


def test_to_binary_endpoint_rejects_negative_n():
    response = client.get("/to-binary?n=-1")
    assert response.status_code == 400
    assert response.json() == {"detail": "n must be non-negative"}

def test_count_vowels_endpoint():
    response = client.get("/count-vowels", params={"text": "Hello World"})
    assert response.status_code == 200
    assert response.json() == {"result": 3}


def test_count_vowels_endpoint_calls_helper(monkeypatch):
    calls = []

    def tracked_count_vowels(text):
        calls.append(text)
        return 99

    monkeypatch.setattr("src.app.count_vowels", tracked_count_vowels)
    response = client.get("/count-vowels", params={"text": "Hello"})
    assert response.status_code == 200
    assert response.json() == {"result": 99}
    assert calls == ["Hello"]


def test_count_vowels_endpoint_accepts_empty_text():
    response = client.get("/count-vowels?text=")
    assert response.status_code == 200
    assert response.json() == {"result": 0}

@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [("listen", "silent", True), ("hello", "world", False)],
)
def test_is_anagram_endpoint(a, b, expected):
    response = client.get("/is-anagram", params={"a": a, "b": b})
    assert response.status_code == 200
    assert response.json() == {"is_anagram": expected}


def test_is_anagram_endpoint_calls_helper(monkeypatch):
    calls = []

    def tracked_is_anagram(a, b):
        calls.append((a, b))
        return True

    monkeypatch.setattr("src.app.is_anagram", tracked_is_anagram)
    response = client.get("/is-anagram", params={"a": "hello", "b": "world"})
    assert response.status_code == 200
    assert response.json() == {"is_anagram": True}
    assert calls == [("hello", "world")]

def test_compound_interest_endpoint():
    response = client.get(
        "/compound-interest",
        params={"principal": 1000, "rate": 0.05, "years": 2},
    )
    assert response.status_code == 200
    assert response.json()["result"] == pytest.approx(1102.5)


def test_compound_interest_endpoint_calls_helper(monkeypatch):
    calls = []

    def tracked_compound_interest(principal, rate, years):
        calls.append((principal, rate, years))
        return 99.0

    monkeypatch.setattr("src.app.compound_interest", tracked_compound_interest)
    response = client.get(
        "/compound-interest",
        params={"principal": 1000, "rate": 0.05, "years": 2},
    )
    assert response.status_code == 200
    assert response.json() == {"result": 99.0}
    assert calls == [(1000.0, 0.05, 2.0)]


@pytest.mark.parametrize(
    ("principal", "years", "message"),
    [
        (-1, 2, "principal must be non-negative"),
        (1000, -1, "years must be non-negative"),
    ],
)
def test_compound_interest_endpoint_rejects_negative_input(
    principal, years, message
):
    response = client.get(
        "/compound-interest",
        params={"principal": principal, "rate": 0.05, "years": years},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": message}

def test_bmi_endpoint():
    response = client.get("/bmi?weight=70&height=1.75")
    assert response.status_code == 200
    assert response.json() == {"bmi": 22.86, "category": "normal"}


def test_bmi_endpoint_calls_helpers(monkeypatch):
    calls = []

    def tracked_calculate(weight, height):
        calls.append(("calculate", weight, height))
        return 27.5

    def tracked_classify(bmi_value):
        calls.append(("classify", bmi_value))
        return "tracked"

    monkeypatch.setattr("src.app.calculate_bmi", tracked_calculate)
    monkeypatch.setattr("src.app.classify_bmi", tracked_classify)
    response = client.get("/bmi?weight=70&height=1.75")
    assert response.status_code == 200
    assert response.json() == {"bmi": 27.5, "category": "tracked"}
    assert calls == [("calculate", 70.0, 1.75), ("classify", 27.5)]


@pytest.mark.parametrize(
    ("weight", "height", "message"),
    [
        (0, 1.75, "weight must be a positive finite number"),
        (70, 0, "height must be a positive finite number"),
    ],
)
def test_bmi_endpoint_rejects_invalid_input(weight, height, message):
    response = client.get(
        "/bmi", params={"weight": weight, "height": height}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": message}

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

from datetime import date

import pytest
from fastapi.testclient import TestClient

from src.app import app, expense_tracker
from src.expense_tracker.tracker import ExpenseTracker

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_transactions():
    expense_tracker.transactions.clear()
    yield
    expense_tracker.transactions.clear()


def simple_mean(numbers):
    return sum(numbers) / len(numbers)


def simple_sort(numbers):
    return sorted(numbers)


def test_add_and_list_transactions():
    tracker = ExpenseTracker(simple_mean, simple_sort)
    transaction_id = tracker.add_transaction(
        "expense", 25, "Food", date(2026, 8, 10), "Lunch"
    )

    transactions = tracker.list_transactions()
    assert len(transactions) == 1
    saved_id, transaction = transactions[0]
    assert saved_id == transaction_id
    assert transaction.transaction_type == "expense"
    assert transaction.amount == 25
    assert transaction.category == "Food"
    assert transaction.occurred_on == date(2026, 8, 10)
    assert transaction.description == "Lunch"


@pytest.mark.parametrize(
    ("transaction_type", "amount", "category", "message"),
    [
        ("other", 10, "Food", "type must be 'income' or 'expense'"),
        ("expense", 0, "Food", "amount must be a positive finite number"),
        ("income", -1, "Salary", "amount must be a positive finite number"),
        ("expense", 10, " ", "category must not be empty"),
    ],
)
def test_transaction_validation(transaction_type, amount, category, message):
    tracker = ExpenseTracker(simple_mean, simple_sort)
    with pytest.raises(ValueError, match=message):
        tracker.add_transaction(
            transaction_type, amount, category, date(2026, 8, 10)
        )


def test_monthly_report_summarizes_income_and_expenses():
    tracker = ExpenseTracker(simple_mean, simple_sort)
    tracker.add_transaction("income", 1000, "Salary", date(2026, 8, 1))
    tracker.add_transaction("expense", 100, "Food", date(2026, 8, 2))
    tracker.add_transaction("expense", 50, "Food", date(2026, 8, 3))
    tracker.add_transaction("income", 500, "Salary", date(2026, 9, 1))

    assert tracker.monthly_report() == [
        {
            "month": "2026-08",
            "income": 1000,
            "expense": 150,
            "net": 850,
            "count": 3,
            "average_amount": pytest.approx(1150 / 3),
            "sorted_amounts": [50, 100, 1000],
        },
        {
            "month": "2026-09",
            "income": 500,
            "expense": 0,
            "net": 500,
            "count": 1,
            "average_amount": 500,
            "sorted_amounts": [500],
        },
    ]


def test_category_report_summarizes_transactions():
    tracker = ExpenseTracker(simple_mean, simple_sort)
    tracker.add_transaction("expense", 30, "Food", date(2026, 8, 1))
    tracker.add_transaction("expense", 10, "Food", date(2026, 9, 1))
    tracker.add_transaction("income", 1000, "Salary", date(2026, 8, 1))

    assert tracker.category_report() == [
        {
            "category": "Food",
            "income": 0,
            "expense": 40,
            "net": -40,
            "count": 2,
            "average_amount": 20,
            "sorted_amounts": [10, 30],
        },
        {
            "category": "Salary",
            "income": 1000,
            "expense": 0,
            "net": 1000,
            "count": 1,
            "average_amount": 1000,
            "sorted_amounts": [1000],
        },
    ]


def test_reports_reuse_injected_mean_and_sort_helpers():
    calls = []

    def tracked_mean(numbers):
        calls.append(("mean", numbers))
        return 99

    def tracked_sort(numbers):
        calls.append(("sort", numbers))
        return [77]

    tracker = ExpenseTracker(tracked_mean, tracked_sort)
    tracker.add_transaction("expense", 25, "Food", date(2026, 8, 1))
    report = tracker.monthly_report()[0]

    assert report["average_amount"] == 99
    assert report["sorted_amounts"] == [77]
    assert calls == [("mean", [25]), ("sort", [25])]


def test_transaction_endpoint_lifecycle():
    first = client.post(
        "/transactions",
        json={
            "type": "income",
            "amount": 1000,
            "category": "Salary",
            "occurred_on": "2026-08-01",
            "description": "August salary",
        },
    )
    second = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": 150,
            "category": "Food",
            "occurred_on": "2026-08-02",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200

    transactions = client.get("/transactions")
    assert transactions.status_code == 200
    assert len(transactions.json()) == 2
    assert transactions.json()[0]["description"] == "August salary"

    monthly = client.get("/reports/monthly")
    assert monthly.status_code == 200
    assert monthly.json() == [
        {
            "month": "2026-08",
            "income": 1000.0,
            "expense": 150.0,
            "net": 850.0,
            "count": 2,
            "average_amount": 575.0,
            "sorted_amounts": [150.0, 1000.0],
        }
    ]

    categories = client.get("/reports/categories")
    assert categories.status_code == 200
    assert [item["category"] for item in categories.json()] == [
        "Food",
        "Salary",
    ]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"type": "other", "amount": 10, "category": "Food"},
            "type must be 'income' or 'expense'",
        ),
        (
            {"type": "expense", "amount": 0, "category": "Food"},
            "amount must be a positive finite number",
        ),
        (
            {"type": "expense", "amount": 10, "category": ""},
            "category must not be empty",
        ),
    ],
)
def test_transaction_endpoint_returns_400(payload, message):
    response = client.post("/transactions", json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": message}


def test_transaction_endpoint_defaults_to_today():
    response = client.post(
        "/transactions",
        json={"type": "expense", "amount": 10, "category": "Food"},
    )
    assert response.status_code == 200
    assert response.json()["occurred_on"] == date.today().isoformat()


def test_transaction_endpoint_calls_tracker(monkeypatch):
    calls = []
    original_add = expense_tracker.add_transaction

    def tracked_add(
        transaction_type, amount, category, occurred_on, description
    ):
        calls.append(
            (transaction_type, amount, category, occurred_on, description)
        )
        return original_add(
            transaction_type, amount, category, occurred_on, description
        )

    monkeypatch.setattr(expense_tracker, "add_transaction", tracked_add)
    response = client.post(
        "/transactions",
        json={
            "type": "expense",
            "amount": 25,
            "category": "Food",
            "occurred_on": "2026-08-10",
            "description": "Lunch",
        },
    )
    assert response.status_code == 200
    assert calls == [
        ("expense", 25.0, "Food", date(2026, 8, 10), "Lunch")
    ]

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.bank_account import BankAccount, account_registry

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_account_registry():
    account_registry.clear()
    yield
    account_registry.clear()


def test_bank_accounts_have_independent_state():
    first = BankAccount()
    second = BankAccount(10)

    first.deposit(25)
    second.deposit(5)

    assert first.get_balance() == 25
    assert second.get_balance() == 15


@pytest.mark.parametrize("amount", [0, -1])
def test_deposit_rejects_non_positive_amount(amount):
    account = BankAccount()
    with pytest.raises(ValueError, match="amount must be a positive finite number"):
        account.deposit(amount)


def test_withdraw_updates_balance():
    account = BankAccount(100)
    account.withdraw(40)
    assert account.get_balance() == 60


@pytest.mark.parametrize(
    ("amount", "message"),
    [(0, "amount must be a positive finite number"), (-1, "amount must be a positive finite number"), (101, "insufficient funds")],
)
def test_withdraw_rejects_invalid_amount(amount, message):
    account = BankAccount(100)
    with pytest.raises(ValueError, match=message):
        account.withdraw(amount)


def test_create_account_with_default_balance():
    response = client.post("/accounts")

    assert response.status_code == 200
    account_id = response.json()["account_id"]
    assert account_registry[account_id].get_balance() == 0


def test_create_account_with_initial_balance():
    response = client.post("/accounts", json={"initial_balance": 75})

    assert response.status_code == 200
    account_id = response.json()["account_id"]
    assert account_registry[account_id].get_balance() == 75


def test_create_account_rejects_negative_initial_balance():
    response = client.post("/accounts", json={"initial_balance": -1})
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "initial_balance must be a non-negative finite number"
    )


def test_account_endpoint_lifecycle():
    create_response = client.post("/accounts", json={"initial_balance": 100})
    account_id = create_response.json()["account_id"]

    deposit_response = client.post(
        f"/accounts/{account_id}/deposit", json={"amount": 25}
    )
    assert deposit_response.status_code == 200
    assert deposit_response.json() == {"balance": 125.0}

    withdraw_response = client.post(
        f"/accounts/{account_id}/withdraw", json={"amount": 40}
    )
    assert withdraw_response.status_code == 200
    assert withdraw_response.json() == {"balance": 85.0}

    balance_response = client.get(f"/accounts/{account_id}/balance")
    assert balance_response.status_code == 200
    assert balance_response.json() == {"balance": 85.0}


@pytest.mark.parametrize(
    ("path", "amount", "message"),
    [
        ("deposit", 0, "amount must be a positive finite number"),
        ("withdraw", 0, "amount must be a positive finite number"),
        ("withdraw", 101, "insufficient funds"),
    ],
)
def test_transaction_endpoints_return_400(path, amount, message):
    account_registry["account"] = BankAccount(100)
    response = client.post(f"/accounts/account/{path}", json={"amount": amount})
    assert response.status_code == 400
    assert response.json() == {"detail": message}


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        (client.post, "/accounts/missing/deposit", {"json": {"amount": 1}}),
        (client.post, "/accounts/missing/withdraw", {"json": {"amount": 1}}),
        (client.get, "/accounts/missing/balance", {}),
    ],
)
def test_account_endpoints_return_404(method, path, kwargs):
    response = method(path, **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}


def test_account_endpoints_call_account_methods():
    class TrackedAccount:
        def __init__(self):
            self.calls = []

        def deposit(self, amount):
            self.calls.append(("deposit", amount))

        def withdraw(self, amount):
            self.calls.append(("withdraw", amount))

        def get_balance(self):
            self.calls.append(("get_balance",))
            return 42

    account = TrackedAccount()
    account_registry["tracked"] = account

    assert client.post(
        "/accounts/tracked/deposit", json={"amount": 10}
    ).json() == {"balance": 42}
    assert client.post(
        "/accounts/tracked/withdraw", json={"amount": 5}
    ).json() == {"balance": 42}
    assert client.get("/accounts/tracked/balance").json() == {"balance": 42}
    assert account.calls == [
        ("deposit", 10.0),
        ("get_balance",),
        ("withdraw", 5.0),
        ("get_balance",),
        ("get_balance",),
    ]

from math import isfinite


class BankAccount:
    def __init__(self, initial_balance: int | float = 0) -> None:
        if not isfinite(initial_balance) or initial_balance < 0:
            raise ValueError("initial_balance must be a non-negative finite number")
        self.balance = initial_balance

    def deposit(self, amount: int | float) -> None:
        if not isfinite(amount) or amount <= 0:
            raise ValueError("amount must be a positive finite number")
        self.balance += amount

    def withdraw(self, amount: int | float) -> None:
        if not isfinite(amount) or amount <= 0:
            raise ValueError("amount must be a positive finite number")
        if amount > self.balance:
            raise ValueError("insufficient funds")
        self.balance -= amount

    def get_balance(self) -> int | float:
        return self.balance


account_registry: dict[str, BankAccount] = {}

from collections.abc import Callable
from datetime import date
from math import isfinite
from uuid import uuid4


class Transaction:
    def __init__(
        self,
        transaction_type: str,
        amount: int | float,
        category: str,
        occurred_on: date,
        description: str = "",
    ) -> None:
        if transaction_type not in {"income", "expense"}:
            raise ValueError("type must be 'income' or 'expense'")
        if not isfinite(amount) or amount <= 0:
            raise ValueError("amount must be a positive finite number")
        if not category.strip():
            raise ValueError("category must not be empty")

        self.transaction_type = transaction_type
        self.amount = amount
        self.category = category.strip()
        self.occurred_on = occurred_on
        self.description = description


class ExpenseTracker:
    def __init__(
        self,
        mean_function: Callable[[list[int | float]], float],
        sort_function: Callable[
            [list[int | float]], list[int | float]
        ],
    ) -> None:
        self.transactions: dict[str, Transaction] = {}
        self.mean_function = mean_function
        self.sort_function = sort_function

    def add_transaction(
        self,
        transaction_type: str,
        amount: int | float,
        category: str,
        occurred_on: date,
        description: str = "",
    ) -> str:
        transaction_id = uuid4().hex
        self.transactions[transaction_id] = Transaction(
            transaction_type,
            amount,
            category,
            occurred_on,
            description,
        )
        return transaction_id

    def list_transactions(self) -> list[tuple[str, Transaction]]:
        return list(self.transactions.items())

    def monthly_report(self) -> list[dict]:
        groups: dict[str, list[Transaction]] = {}
        for transaction in self.transactions.values():
            month = transaction.occurred_on.strftime("%Y-%m")
            groups.setdefault(month, []).append(transaction)
        return self._build_reports(groups, "month")

    def category_report(self) -> list[dict]:
        groups: dict[str, list[Transaction]] = {}
        for transaction in self.transactions.values():
            groups.setdefault(transaction.category, []).append(transaction)
        return self._build_reports(groups, "category")

    def _build_reports(
        self, groups: dict[str, list[Transaction]], group_name: str
    ) -> list[dict]:
        reports = []
        for group_value, transactions in groups.items():
            amounts = [transaction.amount for transaction in transactions]
            income = sum(
                transaction.amount
                for transaction in transactions
                if transaction.transaction_type == "income"
            )
            expense = sum(
                transaction.amount
                for transaction in transactions
                if transaction.transaction_type == "expense"
            )
            reports.append(
                {
                    group_name: group_value,
                    "income": income,
                    "expense": expense,
                    "net": income - expense,
                    "count": len(transactions),
                    "average_amount": self.mean_function(amounts),
                    "sorted_amounts": self.sort_function(amounts),
                }
            )
        reports.sort(key=lambda report: report[group_name])
        return reports

from uuid import uuid4

from src.library.book import Catalog
from src.library.member import MemberRegistry


class Loan:
    def __init__(self, book_id: str, member_id: str) -> None:
        self.book_id = book_id
        self.member_id = member_id
        self.is_returned = False


class LoanManager:
    def __init__(self, catalog: Catalog, member_registry: MemberRegistry) -> None:
        self.catalog = catalog
        self.member_registry = member_registry
        self.loans: dict[str, Loan] = {}

    def borrow_book(self, book_id: str, member_id: str) -> str:
        book = self.catalog.find_book(book_id)
        if book is None:
            raise ValueError("book not found")
        if self.member_registry.find_member(member_id) is None:
            raise ValueError("member not found")
        if book.is_borrowed:
            raise ValueError("book is already borrowed")

        book.is_borrowed = True
        loan_id = uuid4().hex
        self.loans[loan_id] = Loan(book_id, member_id)
        return loan_id

    def return_book(self, loan_id: str) -> None:
        loan = self.loans.get(loan_id)
        if loan is None:
            raise ValueError("loan not found")
        if loan.is_returned:
            raise ValueError("loan has already been returned")

        book = self.catalog.find_book(loan.book_id)
        if book is None:
            raise ValueError("book not found")
        book.is_borrowed = False
        loan.is_returned = True

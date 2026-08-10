import pytest
from fastapi.testclient import TestClient

from src.app import app, catalog, loan_manager, member_registry
from src.library.book import Book, Catalog
from src.library.loan import LoanManager
from src.library.member import Member, MemberRegistry

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_library_state():
    catalog.books.clear()
    member_registry.members.clear()
    loan_manager.loans.clear()
    yield
    catalog.books.clear()
    member_registry.members.clear()
    loan_manager.loans.clear()


def test_catalog_adds_and_finds_book():
    local_catalog = Catalog()
    book_id = local_catalog.add_book("Dune", "Frank Herbert")

    book = local_catalog.find_book(book_id)
    assert isinstance(book, Book)
    assert book.title == "Dune"
    assert book.author == "Frank Herbert"
    assert book.is_borrowed is False
    assert local_catalog.find_book("missing") is None


def test_member_registry_registers_and_finds_member():
    registry = MemberRegistry()
    member_id = registry.register("Alice", "alice@example.com")

    member = registry.find_member(member_id)
    assert isinstance(member, Member)
    assert member.name == "Alice"
    assert member.email == "alice@example.com"
    assert registry.find_member("missing") is None


def test_loan_manager_borrows_and_returns_book():
    local_catalog = Catalog()
    registry = MemberRegistry()
    manager = LoanManager(local_catalog, registry)
    book_id = local_catalog.add_book("Dune", "Frank Herbert")
    member_id = registry.register("Alice", "alice@example.com")

    loan_id = manager.borrow_book(book_id, member_id)
    assert local_catalog.find_book(book_id).is_borrowed is True
    assert manager.loans[loan_id].book_id == book_id
    assert manager.loans[loan_id].member_id == member_id

    manager.return_book(loan_id)
    assert local_catalog.find_book(book_id).is_borrowed is False
    assert manager.loans[loan_id].is_returned is True


def test_borrow_book_calls_catalog_and_member_helpers():
    book = Book("Dune", "Frank Herbert")

    class TrackedCatalog:
        def __init__(self):
            self.calls = []

        def find_book(self, book_id):
            self.calls.append(book_id)
            return book

    class TrackedRegistry:
        def __init__(self):
            self.calls = []

        def find_member(self, member_id):
            self.calls.append(member_id)
            return Member("Alice", "alice@example.com")

    tracked_catalog = TrackedCatalog()
    tracked_registry = TrackedRegistry()
    manager = LoanManager(tracked_catalog, tracked_registry)

    manager.borrow_book("book", "member")
    assert tracked_catalog.calls == ["book"]
    assert tracked_registry.calls == ["member"]
    assert book.is_borrowed is True


@pytest.mark.parametrize(
    ("book_exists", "member_exists", "borrowed", "message"),
    [
        (False, True, False, "book not found"),
        (True, False, False, "member not found"),
        (True, True, True, "book is already borrowed"),
    ],
)
def test_borrow_book_rejects_invalid_request(
    book_exists, member_exists, borrowed, message
):
    local_catalog = Catalog()
    registry = MemberRegistry()
    manager = LoanManager(local_catalog, registry)
    book_id = local_catalog.add_book("Dune", "Frank Herbert")
    member_id = registry.register("Alice", "alice@example.com")
    local_catalog.find_book(book_id).is_borrowed = borrowed

    requested_book_id = book_id if book_exists else "missing"
    requested_member_id = member_id if member_exists else "missing"
    with pytest.raises(ValueError, match=message):
        manager.borrow_book(requested_book_id, requested_member_id)


def test_return_book_rejects_missing_or_already_returned_loan():
    local_catalog = Catalog()
    registry = MemberRegistry()
    manager = LoanManager(local_catalog, registry)

    with pytest.raises(ValueError, match="loan not found"):
        manager.return_book("missing")

    book_id = local_catalog.add_book("Dune", "Frank Herbert")
    member_id = registry.register("Alice", "alice@example.com")
    loan_id = manager.borrow_book(book_id, member_id)
    manager.return_book(loan_id)
    with pytest.raises(ValueError, match="loan has already been returned"):
        manager.return_book(loan_id)


def test_add_and_list_books_endpoints():
    create_response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert"}
    )
    assert create_response.status_code == 200
    book_id = create_response.json()["book_id"]

    list_response = client.get("/books")
    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "book_id": book_id,
            "title": "Dune",
            "author": "Frank Herbert",
            "is_borrowed": False,
        }
    ]


def test_add_book_endpoint_calls_catalog_helper(monkeypatch):
    calls = []

    def tracked_add_book(title, author):
        calls.append((title, author))
        return "book-id"

    monkeypatch.setattr(catalog, "add_book", tracked_add_book)
    response = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert"}
    )
    assert response.json() == {"book_id": "book-id"}
    assert calls == [("Dune", "Frank Herbert")]


def test_register_and_get_member_endpoints():
    create_response = client.post(
        "/members", json={"name": "Alice", "email": "alice@example.com"}
    )
    assert create_response.status_code == 200
    member_id = create_response.json()["member_id"]

    get_response = client.get(f"/members/{member_id}")
    assert get_response.status_code == 200
    assert get_response.json() == {
        "name": "Alice",
        "email": "alice@example.com",
    }


def test_member_endpoints_call_registry_helpers(monkeypatch):
    register_calls = []
    find_calls = []

    def tracked_register(name, email):
        register_calls.append((name, email))
        return "member-id"

    def tracked_find(member_id):
        find_calls.append(member_id)
        return Member("Alice", "alice@example.com")

    monkeypatch.setattr(member_registry, "register", tracked_register)
    monkeypatch.setattr(member_registry, "find_member", tracked_find)

    assert client.post(
        "/members", json={"name": "Alice", "email": "alice@example.com"}
    ).json() == {"member_id": "member-id"}
    assert client.get("/members/member-id").json() == {
        "name": "Alice",
        "email": "alice@example.com",
    }
    assert register_calls == [("Alice", "alice@example.com")]
    assert find_calls == ["member-id"]


def test_get_member_endpoint_returns_404():
    response = client.get("/members/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Member not found"}


def test_borrow_and_return_endpoints_update_catalog():
    book_id = client.post(
        "/books", json={"title": "Dune", "author": "Frank Herbert"}
    ).json()["book_id"]
    member_id = client.post(
        "/members", json={"name": "Alice", "email": "alice@example.com"}
    ).json()["member_id"]

    borrow_response = client.post(
        "/loans", json={"book_id": book_id, "member_id": member_id}
    )
    assert borrow_response.status_code == 200
    loan_id = borrow_response.json()["loan_id"]
    assert client.get("/books").json()[0]["is_borrowed"] is True

    return_response = client.post(f"/loans/{loan_id}/return")
    assert return_response.status_code == 200
    assert return_response.json() == {"status": "returned"}
    assert client.get("/books").json()[0]["is_borrowed"] is False


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"book_id": "missing", "member_id": "missing"}, "book not found"),
    ],
)
def test_borrow_endpoint_returns_400(payload, message):
    response = client.post("/loans", json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": message}


def test_loan_endpoints_call_manager_helpers(monkeypatch):
    borrow_calls = []
    return_calls = []

    def tracked_borrow(book_id, member_id):
        borrow_calls.append((book_id, member_id))
        return "loan-id"

    def tracked_return(loan_id):
        return_calls.append(loan_id)

    monkeypatch.setattr(loan_manager, "borrow_book", tracked_borrow)
    monkeypatch.setattr(loan_manager, "return_book", tracked_return)

    assert client.post(
        "/loans", json={"book_id": "book", "member_id": "member"}
    ).json() == {"loan_id": "loan-id"}
    assert client.post("/loans/loan-id/return").json() == {"status": "returned"}
    assert borrow_calls == [("book", "member")]
    assert return_calls == ["loan-id"]


def test_return_endpoint_returns_400_for_invalid_loan():
    response = client.post("/loans/missing/return")
    assert response.status_code == 400
    assert response.json() == {"detail": "loan not found"}

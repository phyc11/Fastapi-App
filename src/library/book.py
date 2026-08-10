from uuid import uuid4


class Book:
    def __init__(self, title: str, author: str) -> None:
        self.title = title
        self.author = author
        self.is_borrowed = False


class Catalog:
    def __init__(self) -> None:
        self.books: dict[str, Book] = {}

    def add_book(self, title: str, author: str) -> str:
        book_id = uuid4().hex
        self.books[book_id] = Book(title, author)
        return book_id

    def find_book(self, book_id: str) -> Book | None:
        return self.books.get(book_id)

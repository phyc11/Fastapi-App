from math import isfinite


class Product:
    def __init__(
        self, name: str, price: int | float, stock: int
    ) -> None:
        if not name.strip():
            raise ValueError("name must not be empty")
        if not isfinite(price) or price < 0:
            raise ValueError("price must be a non-negative finite number")
        if stock < 0:
            raise ValueError("stock must be non-negative")
        self.name = name
        self.price = price
        self.stock = stock


class Cart:
    def __init__(self, cart_id: str) -> None:
        self.cart_id = cart_id
        self.items: dict[str, int] = {}
        self.is_checked_out = False

    def add_item(self, product_id: str, quantity: int) -> None:
        if self.is_checked_out:
            raise ValueError("cart has already been checked out")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self.items[product_id] = self.items.get(product_id, 0) + quantity

    def remove_item(self, product_id: str) -> None:
        if self.is_checked_out:
            raise ValueError("cart has already been checked out")
        if product_id not in self.items:
            raise ValueError("product is not in cart")
        del self.items[product_id]


class Order:
    def __init__(
        self,
        order_id: str,
        cart_id: str,
        items: dict[str, int],
        total: int | float,
    ) -> None:
        self.order_id = order_id
        self.cart_id = cart_id
        self.items = items
        self.total = total

from datetime import datetime, timezone
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
        user_id: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.order_id = order_id
        self.cart_id = cart_id
        self.items = items
        self.total = total
        self.user_id = user_id
        self.status = "pending"
        self.created_at = now
        self.updated_at = now

    def update_status(self, new_status: str) -> None:
        allowed_transitions = {
            "pending": {"paid", "cancelled"},
            "paid": {"shipped", "cancelled"},
            "shipped": {"delivered"},
            "delivered": set(),
            "cancelled": set(),
        }
        if new_status not in allowed_transitions:
            raise ValueError("invalid order status")
        if new_status not in allowed_transitions[self.status]:
            raise ValueError(
                f"cannot change order status from {self.status} to {new_status}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

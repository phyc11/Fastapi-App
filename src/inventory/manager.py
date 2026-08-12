from datetime import datetime, timezone
from uuid import uuid4


class StockMovement:
    def __init__(
        self,
        movement_type: str,
        quantity: int,
        stock_after: int,
    ) -> None:
        self.movement_id = uuid4().hex
        self.movement_type = movement_type
        self.quantity = quantity
        self.stock_after = stock_after
        self.created_at = datetime.now(timezone.utc)


class InventoryProduct:
    def __init__(self, name: str, initial_stock: int = 0) -> None:
        if not name.strip():
            raise ValueError("name must not be empty")
        if initial_stock < 0:
            raise ValueError("initial_stock must be non-negative")
        self.name = name
        self.stock = initial_stock
        self.history: list[StockMovement] = []
        if initial_stock > 0:
            self.history.append(
                StockMovement("initial", initial_stock, initial_stock)
            )

    def stock_in(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self.stock += quantity
        self.history.append(StockMovement("stock_in", quantity, self.stock))

    def stock_out(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if quantity > self.stock:
            raise ValueError("insufficient stock")
        self.stock -= quantity
        self.history.append(StockMovement("stock_out", quantity, self.stock))


class InventoryManager:
    def __init__(self) -> None:
        self.products: dict[str, InventoryProduct] = {}

    def add_product(self, name: str, initial_stock: int = 0) -> str:
        product_id = uuid4().hex
        self.products[product_id] = InventoryProduct(name, initial_stock)
        return product_id

    def find_product(self, product_id: str) -> InventoryProduct | None:
        return self.products.get(product_id)

    def stock_in(self, product_id: str, quantity: int) -> InventoryProduct:
        product = self.find_product(product_id)
        if product is None:
            raise KeyError("product not found")
        product.stock_in(quantity)
        return product

    def stock_out(self, product_id: str, quantity: int) -> InventoryProduct:
        product = self.find_product(product_id)
        if product is None:
            raise KeyError("product not found")
        product.stock_out(quantity)
        return product

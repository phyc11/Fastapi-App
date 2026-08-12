from uuid import uuid4

from src.shop.models import Product


class ProductCatalog:
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}

    def add_product(self, name: str, price: int | float, stock: int) -> str:
        product_id = uuid4().hex
        self.products[product_id] = Product(name, price, stock)
        return product_id

    def find_product(self, product_id: str) -> Product | None:
        return self.products.get(product_id)

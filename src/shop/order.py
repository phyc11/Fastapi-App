from uuid import uuid4

from src.shop.cart import CartRegistry
from src.shop.catalog import ProductCatalog
from src.shop.models import Order


class OrderManager:
    def __init__(
        self, product_catalog: ProductCatalog, cart_registry: CartRegistry
    ) -> None:
        self.product_catalog = product_catalog
        self.cart_registry = cart_registry
        self.orders: dict[str, Order] = {}

    def create_order(self, cart_id: str) -> str:
        cart = self.cart_registry.find_cart(cart_id)
        if cart is None:
            raise ValueError("cart not found")
        if cart.is_checked_out:
            raise ValueError("cart has already been checked out")
        if not cart.items:
            raise ValueError("cart is empty")

        products = {}
        for product_id, quantity in cart.items.items():
            product = self.product_catalog.find_product(product_id)
            if product is None:
                raise ValueError("product not found")
            if quantity > product.stock:
                raise ValueError("insufficient stock")
            products[product_id] = product

        total = self.cart_registry.total(cart)
        for product_id, quantity in cart.items.items():
            products[product_id].stock -= quantity

        order_id = uuid4().hex
        self.orders[order_id] = Order(
            order_id, cart_id, cart.items.copy(), total
        )
        cart.is_checked_out = True
        return order_id

    def find_order(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

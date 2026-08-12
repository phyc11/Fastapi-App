from src.shop.catalog import ProductCatalog
from src.shop.models import Cart


class CartRegistry:
    def __init__(self, product_catalog: ProductCatalog) -> None:
        self.product_catalog = product_catalog
        self.carts: dict[str, Cart] = {}

    def get_or_create(self, cart_id: str) -> Cart:
        if not cart_id.strip():
            raise ValueError("cart_id must not be empty")
        if cart_id not in self.carts:
            self.carts[cart_id] = Cart(cart_id)
        return self.carts[cart_id]

    def find_cart(self, cart_id: str) -> Cart | None:
        return self.carts.get(cart_id)

    def add_item(self, cart_id: str, product_id: str, quantity: int) -> Cart:
        product = self.product_catalog.find_product(product_id)
        if product is None:
            raise ValueError("product not found")

        cart = self.get_or_create(cart_id)
        requested_quantity = cart.items.get(product_id, 0) + quantity
        if requested_quantity > product.stock:
            raise ValueError("insufficient stock")
        cart.add_item(product_id, quantity)
        return cart

    def remove_item(self, cart_id: str, product_id: str) -> Cart:
        cart = self.find_cart(cart_id)
        if cart is None:
            raise ValueError("cart not found")
        cart.remove_item(product_id)
        return cart

    def total(self, cart: Cart) -> int | float:
        total = 0
        for product_id, quantity in cart.items.items():
            product = self.product_catalog.find_product(product_id)
            if product is None:
                raise ValueError("product not found")
            total += product.price * quantity
        return total

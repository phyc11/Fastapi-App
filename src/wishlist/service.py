from datetime import datetime, timezone

from src.shop.cart import CartRegistry
from src.shop.catalog import ProductCatalog
from src.shop.models import Cart, Product


class Wishlist:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.product_ids: list[str] = []
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now

    def add_product(self, product_id: str) -> bool:
        if product_id not in self.product_ids:
            self.product_ids.append(product_id)
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def remove_product(self, product_id: str) -> bool:
        if product_id in self.product_ids:
            self.product_ids.remove(product_id)
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def has_product(self, product_id: str) -> bool:
        return product_id in self.product_ids


class WishlistService:
    def __init__(
        self,
        product_catalog: ProductCatalog,
        cart_registry: CartRegistry,
    ) -> None:
        self.product_catalog = product_catalog
        self.cart_registry = cart_registry
        self.wishlists: dict[str, Wishlist] = {}

    def get_or_create_wishlist(self, user_id: str) -> Wishlist:
        if user_id not in self.wishlists:
            self.wishlists[user_id] = Wishlist(user_id)
        return self.wishlists[user_id]

    def add_item(self, user_id: str, product_id: str) -> Wishlist:
        product = self.product_catalog.find_product(product_id)
        if product is None:
            raise KeyError("product not found")
        wishlist = self.get_or_create_wishlist(user_id)
        wishlist.add_product(product_id)
        return wishlist

    def remove_item(self, user_id: str, product_id: str) -> Wishlist:
        wishlist = self.get_or_create_wishlist(user_id)
        if not wishlist.has_product(product_id):
            raise KeyError("product not found in wishlist")
        wishlist.remove_product(product_id)
        return wishlist

    def get_user_wishlist_products(self, user_id: str) -> list[dict]:
        wishlist = self.get_or_create_wishlist(user_id)
        products = []
        for product_id in wishlist.product_ids:
            product = self.product_catalog.find_product(product_id)
            if product is not None:
                products.append(
                    {
                        "product_id": product_id,
                        "name": product.name,
                        "price": product.price,
                        "stock": product.stock,
                    }
                )
        return products

    def move_to_cart(
        self, user_id: str, product_id: str, cart_id: str, quantity: int = 1
    ) -> Cart:
        wishlist = self.get_or_create_wishlist(user_id)
        if not wishlist.has_product(product_id):
            raise KeyError("product not found in wishlist")

        # Adding to cart validates product existence and stock
        cart = self.cart_registry.add_item(cart_id, product_id, quantity)
        wishlist.remove_product(product_id)
        return cart

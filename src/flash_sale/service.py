from datetime import datetime, timezone
from uuid import uuid4

from src.shop.catalog import ProductCatalog


class FlashSaleItem:
    def __init__(
        self,
        product_id: str,
        flash_price: float,
        quantity_limit: int,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        if flash_price <= 0:
            raise ValueError("flash_price must be positive")
        if quantity_limit <= 0:
            raise ValueError("quantity_limit must be positive")

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")

        self.flash_sale_id = uuid4().hex
        self.product_id = product_id
        self.flash_price = float(flash_price)
        self.quantity_limit = quantity_limit
        self.sold_count = 0
        self.start_time = start_time
        self.end_time = end_time
        self.is_active = True

    @property
    def remaining_quantity(self) -> int:
        return max(0, self.quantity_limit - self.sold_count)

    def is_currently_active(self, now: datetime | None = None) -> bool:
        if not self.is_active or self.remaining_quantity <= 0:
            return False
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        return self.start_time <= current_time <= self.end_time

    def time_remaining_seconds(self, now: datetime | None = None) -> float:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        if current_time < self.start_time or current_time > self.end_time:
            return 0.0
        return (self.end_time - current_time).total_seconds()


class FlashSaleService:
    def __init__(self, product_catalog: ProductCatalog) -> None:
        self.product_catalog = product_catalog
        self.items: dict[str, FlashSaleItem] = {}

    def create_flash_sale(
        self,
        product_id: str,
        flash_price: float,
        quantity_limit: int,
        start_time: datetime,
        end_time: datetime,
    ) -> FlashSaleItem:
        product = self.product_catalog.find_product(product_id)
        if product is None:
            raise KeyError("product not found")

        item = FlashSaleItem(
            product_id=product_id,
            flash_price=flash_price,
            quantity_limit=quantity_limit,
            start_time=start_time,
            end_time=end_time,
        )
        self.items[item.flash_sale_id] = item
        return item

    def get_active_flash_sales(
        self, now: datetime | None = None
    ) -> list[dict]:
        active_items = []
        for item in self.items.values():
            if item.is_currently_active(now):
                product = self.product_catalog.find_product(item.product_id)
                product_name = product.name if product else "Unknown Product"
                original_price = product.price if product else item.flash_price

                active_items.append(
                    {
                        "flash_sale_id": item.flash_sale_id,
                        "product_id": item.product_id,
                        "product_name": product_name,
                        "original_price": original_price,
                        "flash_price": item.flash_price,
                        "discount_percentage": round(
                            (1 - item.flash_price / original_price) * 100, 2
                        )
                        if original_price > 0
                        else 0.0,
                        "quantity_limit": item.quantity_limit,
                        "remaining_quantity": item.remaining_quantity,
                        "sold_count": item.sold_count,
                        "start_time": item.start_time.isoformat(),
                        "end_time": item.end_time.isoformat(),
                        "time_remaining_seconds": item.time_remaining_seconds(now),
                    }
                )
        return active_items

    def find_active_flash_sale_for_product(
        self, product_id: str, now: datetime | None = None
    ) -> FlashSaleItem | None:
        for item in self.items.values():
            if item.product_id == product_id and item.is_currently_active(now):
                return item
        return None

    def buy_flash_sale_product(
        self,
        product_id: str,
        quantity: int = 1,
        user_id: str | None = None,
        now: datetime | None = None,
    ) -> dict:
        if quantity <= 0:
            raise ValueError("quantity must be positive")

        product = self.product_catalog.find_product(product_id)
        if product is None:
            raise KeyError("product not found")

        flash_sale = self.find_active_flash_sale_for_product(product_id, now)
        if flash_sale is None:
            raise KeyError("no active flash sale for product")

        if quantity > flash_sale.remaining_quantity:
            raise ValueError("exceeds flash sale quantity limit")

        if quantity > product.stock:
            raise ValueError("insufficient stock in catalog")

        product.stock -= quantity
        flash_sale.sold_count += quantity
        total_price = round(flash_sale.flash_price * quantity, 2)
        order_id = uuid4().hex

        return {
            "order_id": order_id,
            "user_id": user_id,
            "product_id": product_id,
            "product_name": product.name,
            "quantity": quantity,
            "unit_flash_price": flash_sale.flash_price,
            "total_price": total_price,
            "purchased_at": (now or datetime.now(timezone.utc)).isoformat(),
        }

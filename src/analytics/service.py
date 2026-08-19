from datetime import datetime, timezone

from src.auth.service import AuthService
from src.inventory.manager import InventoryManager
from src.shop.catalog import ProductCatalog
from src.shop.order import OrderManager

VALID_PERIODS = {"day", "week", "month"}


class AnalyticsService:
    def __init__(
        self,
        order_manager: OrderManager,
        product_catalog: ProductCatalog,
        inventory_manager: InventoryManager,
        auth_service: AuthService,
    ) -> None:
        self.order_manager = order_manager
        self.product_catalog = product_catalog
        self.inventory_manager = inventory_manager
        self.auth_service = auth_service

    def get_dashboard_summary(self) -> dict:
        orders = list(self.order_manager.orders.values())
        total_revenue = round(sum(order.total for order in orders), 2)
        total_orders = len(orders)
        new_users = len(self.auth_service.users)

        product_sales: dict[str, dict] = {}
        for order in orders:
            for product_id, quantity in order.items.items():
                product = self.product_catalog.find_product(product_id)
                product_name = product.name if product else "Unknown Product"
                price = product.price if product else 0.0

                if product_id not in product_sales:
                    product_sales[product_id] = {
                        "product_id": product_id,
                        "name": product_name,
                        "quantity_sold": 0,
                        "revenue": 0.0,
                    }
                product_sales[product_id]["quantity_sold"] += quantity
                product_sales[product_id]["revenue"] = round(
                    product_sales[product_id]["revenue"] + (price * quantity), 2
                )

        sorted_top_products = sorted(
            product_sales.values(),
            key=lambda item: item["quantity_sold"],
            reverse=True,
        )

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "new_users": new_users,
            "top_selling_products": sorted_top_products[:5],
        }

    def get_sales_chart(self, period: str = "day") -> list[dict]:
        period_key = period.strip().lower()
        if period_key not in VALID_PERIODS:
            raise ValueError("period must be 'day', 'week', or 'month'")

        orders = list(self.order_manager.orders.values())
        grouped_sales: dict[str, dict] = {}

        for order in orders:
            created_at = order.created_at
            if period_key == "day":
                key = created_at.strftime("%Y-%m-%d")
            elif period_key == "week":
                key = f"{created_at.isocalendar().year}-W{created_at.isocalendar().week:02d}"
            else:
                key = created_at.strftime("%Y-%m")

            if key not in grouped_sales:
                grouped_sales[key] = {
                    "period": key,
                    "revenue": 0.0,
                    "order_count": 0,
                }
            grouped_sales[key]["revenue"] = round(
                grouped_sales[key]["revenue"] + order.total, 2
            )
            grouped_sales[key]["order_count"] += 1

        return sorted(grouped_sales.values(), key=lambda x: x["period"])

    def get_low_stock_alerts(self, threshold: int = 10) -> list[dict]:
        if threshold < 0:
            raise ValueError("threshold must be non-negative")

        low_stock_items = []
        for product_id, product in self.inventory_manager.products.items():
            if product.stock < threshold:
                low_stock_items.append(
                    {
                        "product_id": product_id,
                        "name": product.name,
                        "stock": product.stock,
                        "source": "inventory",
                        "status": "out_of_stock" if product.stock == 0 else "low_stock",
                    }
                )

        for product_id, product in self.product_catalog.products.items():
            if product.stock < threshold:
                low_stock_items.append(
                    {
                        "product_id": product_id,
                        "name": product.name,
                        "stock": product.stock,
                        "source": "shop",
                        "status": "out_of_stock" if product.stock == 0 else "low_stock",
                    }
                )

        return low_stock_items

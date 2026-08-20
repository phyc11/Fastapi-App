from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.analytics.service import AnalyticsService
from src.app import (
    analytics_service,
    app,
    auth_service,
    cart_registry,
    inventory_manager,
    order_manager,
    product_catalog,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    inventory_manager.products.clear()
    product_catalog.products.clear()
    cart_registry.carts.clear()
    order_manager.orders.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    inventory_manager.products.clear()
    product_catalog.products.clear()
    cart_registry.carts.clear()
    order_manager.orders.clear()


def test_dashboard_summary_calculation():
    # Register 2 users
    auth_service.register("Alice", "alice@example.com", "password123")
    auth_service.register("Bob", "bob@example.com", "password123")

    # Add products
    p1 = product_catalog.add_product("Laptop", 1000.0, 10)
    p2 = product_catalog.add_product("Mouse", 50.0, 50)

    # Create cart and order 1
    cart_id1 = uuid4().hex
    cart_registry.add_item(cart_id1, p1, 2)
    cart_registry.add_item(cart_id1, p2, 1)
    order_manager.create_order(cart_id1)

    # Create cart and order 2
    cart_id2 = uuid4().hex
    cart_registry.add_item(cart_id2, p2, 3)
    order_manager.create_order(cart_id2)

    summary = analytics_service.get_dashboard_summary()

    assert summary["new_users"] == 2
    assert summary["total_orders"] == 2
    assert summary["total_revenue"] == 2200.0

    top_products = summary["top_selling_products"]
    assert len(top_products) == 2
    assert top_products[0]["product_id"] == p2
    assert top_products[0]["quantity_sold"] == 4
    assert top_products[1]["product_id"] == p1
    assert top_products[1]["quantity_sold"] == 2


def test_sales_chart_grouping_by_periods():
    p1 = product_catalog.add_product("Item", 100.0, 20)
    cart_id = uuid4().hex
    cart_registry.add_item(cart_id, p1, 1)
    order_id = order_manager.create_order(cart_id)

    order = order_manager.find_order(order_id)
    order.created_at = datetime(2026, 8, 19, 10, 0, tzinfo=timezone.utc)

    # Test day grouping
    chart_day = analytics_service.get_sales_chart("day")
    assert len(chart_day) == 1
    assert chart_day[0]["period"] == "2026-08-19"
    assert chart_day[0]["revenue"] == 100.0

    # Test month grouping
    chart_month = analytics_service.get_sales_chart("month")
    assert len(chart_month) == 1
    assert chart_month[0]["period"] == "2026-08"

    # Test invalid period
    with pytest.raises(ValueError, match="period must be"):
        analytics_service.get_sales_chart("year")


def test_low_stock_alerts():
    # Add item to inventory with stock 5
    inventory_manager.add_product("Spare Wheel", initial_stock=5)

    # Add item to shop catalog with stock 3
    product_catalog.add_product("Keyboard", 30.0, stock=3)

    # Add item with stock 50 (should not be alerted)
    product_catalog.add_product("Monitor", 300.0, stock=50)

    alerts = analytics_service.get_low_stock_alerts(threshold=10)
    assert len(alerts) == 2
    product_names = {item["name"] for item in alerts}
    assert "Spare Wheel" in product_names
    assert "Keyboard" in product_names

    with pytest.raises(ValueError, match="threshold must be non-negative"):
        analytics_service.get_low_stock_alerts(threshold=-1)


def test_analytics_endpoints_lifecycle():
    p1 = product_catalog.add_product("Headphones", 100.0, 2)
    cart_id = uuid4().hex
    cart_registry.add_item(cart_id, p1, 1)
    order_manager.create_order(cart_id)

    # GET /analytics/dashboard
    res = client.get("/analytics/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["total_orders"] == 1
    assert data["total_revenue"] == 100.0

    # GET /analytics/sales-chart
    res_chart = client.get("/analytics/sales-chart?period=day")
    assert res_chart.status_code == 200
    assert len(res_chart.json()) == 1

    # GET /analytics/sales-chart with invalid period
    res_err = client.get("/analytics/sales-chart?period=invalid")
    assert res_err.status_code == 400

    # GET /analytics/low-stock-alert
    res_alert = client.get("/analytics/low-stock-alert?threshold=5")
    assert res_alert.status_code == 200
    assert len(res_alert.json()) >= 1

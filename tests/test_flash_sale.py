from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service, flash_sale_service, product_catalog
from src.flash_sale.service import FlashSaleService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    product_catalog.products.clear()
    flash_sale_service.items.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    product_catalog.products.clear()
    flash_sale_service.items.clear()


def auth_headers(name="Flash User", email="flash@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def test_flash_sale_service_creation_and_buying():
    service = FlashSaleService(product_catalog)
    p_id = product_catalog.add_product("4K Monitor", 500.0, stock=20)

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=10)
    end_time = now + timedelta(hours=2)

    # 1. Create Flash Sale
    item = service.create_flash_sale(
        product_id=p_id,
        flash_price=299.0,
        quantity_limit=5,
        start_time=start_time,
        end_time=end_time,
    )
    assert item.product_id == p_id
    assert item.flash_price == 299.0
    assert item.remaining_quantity == 5

    # 2. Get active sales
    active = service.get_active_flash_sales(now=now)
    assert len(active) == 1
    assert active[0]["product_name"] == "4K Monitor"
    assert active[0]["flash_price"] == 299.0
    assert active[0]["discount_percentage"] == 40.2  # (1 - 299/500)*100 = 40.2%

    # 3. Buy flash sale item
    res = service.buy_flash_sale_product(p_id, quantity=2, user_id="u1", now=now)
    assert res["quantity"] == 2
    assert res["total_price"] == 598.0
    assert item.sold_count == 2
    assert product_catalog.find_product(p_id).stock == 18

    # 4. Error when exceeding quantity limit (3 left in flash sale)
    with pytest.raises(ValueError, match="exceeds flash sale quantity limit"):
        service.buy_flash_sale_product(p_id, quantity=4, user_id="u1", now=now)


def test_flash_sale_service_validations():
    service = FlashSaleService(product_catalog)
    now = datetime.now(timezone.utc)

    # Missing product
    with pytest.raises(KeyError, match="product not found"):
        service.create_flash_sale(
            "missing_id", 10.0, 5, now, now + timedelta(hours=1)
        )

    p_id = product_catalog.add_product("Headset", 100.0, 10)

    # Invalid end time (end before start)
    with pytest.raises(ValueError, match="end_time must be after start_time"):
        service.create_flash_sale(
            p_id, 50.0, 5, now + timedelta(hours=2), now
        )

    # Non-positive price
    with pytest.raises(ValueError, match="flash_price must be positive"):
        service.create_flash_sale(
            p_id, 0.0, 5, now, now + timedelta(hours=1)
        )


def test_flash_sale_endpoints_lifecycle():
    user, headers = auth_headers()
    p_id = product_catalog.add_product("Smart Speaker", 80.0, stock=15)

    now = datetime.now(timezone.utc)
    start_iso = (now - timedelta(minutes=5)).isoformat()
    end_iso = (now + timedelta(hours=3)).isoformat()

    # 1. Create Flash Sale (POST /flash-sale)
    create_res = client.post(
        "/flash-sale",
        json={
            "product_id": p_id,
            "flash_price": 49.99,
            "quantity_limit": 10,
            "start_time": start_iso,
            "end_time": end_iso,
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["flash_price"] == 49.99
    assert created_data["quantity_limit"] == 10

    # 2. Get Active Sales (GET /flash-sale/active)
    active_res = client.get("/flash-sale/active")
    assert active_res.status_code == 200
    active_items = active_res.json()
    assert len(active_items) == 1
    assert active_items[0]["product_id"] == p_id

    # 3. Buy Flash Sale Product (POST /flash-sale/buy/{product_id})
    buy_res = client.post(
        f"/flash-sale/buy/{p_id}",
        json={"quantity": 2},
        headers=headers,
    )
    assert buy_res.status_code == 200
    buy_data = buy_res.json()
    assert buy_data["quantity"] == 2
    assert buy_data["total_price"] == 99.98


def test_flash_sale_unauthenticated_and_errors():
    p_id = product_catalog.add_product("Mousepad", 20.0, 5)
    now = datetime.now(timezone.utc)

    # 401 Unauthenticated
    assert (
        client.post(
            "/flash-sale",
            json={
                "product_id": p_id,
                "flash_price": 10.0,
                "quantity_limit": 2,
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
            },
        ).status_code
        == 401
    )
    assert client.post(f"/flash-sale/buy/{p_id}", json={"quantity": 1}).status_code == 401

    user, headers = auth_headers()
    # 404 Buying product with no active flash sale
    assert client.post(f"/flash-sale/buy/{p_id}", json={"quantity": 1}, headers=headers).status_code == 404

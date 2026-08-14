import pytest
from fastapi.testclient import TestClient

from src.app import (
    app,
    auth_service,
    cart_registry,
    order_manager,
    product_catalog,
)
from src.shop.models import Order

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    product_catalog.products.clear()
    cart_registry.carts.clear()
    order_manager.orders.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    product_catalog.products.clear()
    cart_registry.carts.clear()
    order_manager.orders.clear()


def auth_headers(name="Alice", email="alice@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def create_cart(cart_id="cart"):
    product_id = product_catalog.add_product("Keyboard", 50, 10)
    cart_registry.add_item(cart_id, product_id, 1)
    return cart_id


def test_order_status_valid_transitions():
    order = Order("order", "cart", {"product": 1}, 50, "user")
    assert order.status == "pending"

    order.update_status("paid")
    order.update_status("shipped")
    order.update_status("delivered")
    assert order.status == "delivered"


def test_order_can_be_cancelled_from_pending_or_paid():
    pending = Order("pending", "cart", {}, 0, "user")
    pending.update_status("cancelled")
    assert pending.status == "cancelled"

    paid = Order("paid", "cart", {}, 0, "user")
    paid.update_status("paid")
    paid.update_status("cancelled")
    assert paid.status == "cancelled"


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("pending", "shipped"),
        ("pending", "delivered"),
        ("paid", "delivered"),
        ("shipped", "cancelled"),
        ("delivered", "cancelled"),
        ("cancelled", "paid"),
    ],
)
def test_order_rejects_invalid_transitions(current, target):
    order = Order("order", "cart", {}, 0, "user")
    if current == "paid":
        order.update_status("paid")
    elif current == "shipped":
        order.update_status("paid")
        order.update_status("shipped")
    elif current == "delivered":
        order.update_status("paid")
        order.update_status("shipped")
        order.update_status("delivered")
    elif current == "cancelled":
        order.update_status("cancelled")

    with pytest.raises(
        ValueError,
        match=f"cannot change order status from {current} to {target}",
    ):
        order.update_status(target)


def test_order_rejects_unknown_status():
    order = Order("order", "cart", {}, 0, "user")
    with pytest.raises(ValueError, match="invalid order status"):
        order.update_status("unknown")


def test_order_manager_filters_and_updates_by_user():
    first_id = order_manager.create_order(create_cart("first"), "user-1")
    second_id = order_manager.create_order(create_cart("second"), "user-2")

    assert [order.order_id for order in order_manager.list_for_user("user-1")] == [
        first_id
    ]
    assert order_manager.find_for_user(first_id, "user-1") is not None
    assert order_manager.find_for_user(second_id, "user-1") is None

    updated = order_manager.update_status(first_id, "user-1", "paid")
    assert updated.status == "paid"
    with pytest.raises(KeyError, match="order not found"):
        order_manager.update_status(second_id, "user-1", "paid")


def test_authenticated_order_history_lifecycle():
    _, headers = auth_headers()
    cart_id = create_cart()

    create_response = client.post(
        "/orders", json={"cart_id": cart_id}, headers=headers
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "pending"
    assert created["total"] == 50.0
    assert created["created_at"]
    assert created["updated_at"]

    list_response = client.get("/orders/me", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json() == [created]

    detail_response = client.get(
        f"/orders/{created['order_id']}", headers=headers
    )
    assert detail_response.status_code == 200
    assert detail_response.json() == created

    for status in ("paid", "shipped", "delivered"):
        response = client.patch(
            f"/orders/{created['order_id']}/status",
            json={"status": status},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == status


def test_users_cannot_see_or_update_other_users_orders():
    _, owner_headers = auth_headers()
    _, other_headers = auth_headers("Bob", "bob@example.com")
    order_id = client.post(
        "/orders", json={"cart_id": create_cart()}, headers=owner_headers
    ).json()["order_id"]

    assert client.get("/orders/me", headers=other_headers).json() == []
    detail = client.get(f"/orders/{order_id}", headers=other_headers)
    assert detail.status_code == 404
    update = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "paid"},
        headers=other_headers,
    )
    assert update.status_code == 404


def test_order_status_endpoint_returns_400_for_invalid_transition():
    _, headers = auth_headers()
    order_id = client.post(
        "/orders", json={"cart_id": create_cart()}, headers=headers
    ).json()["order_id"]

    response = client.patch(
        f"/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "cannot change order status from pending to delivered"
    }


def test_order_history_endpoints_require_authentication():
    assert client.get("/orders/me").status_code == 401
    assert client.get("/orders/id").status_code == 401
    assert client.patch(
        "/orders/id/status", json={"status": "paid"}
    ).status_code == 401


def test_anonymous_checkout_remains_supported_but_has_no_user_history():
    response = client.post("/orders", json={"cart_id": create_cart()})
    assert response.status_code == 200
    order = order_manager.find_order(response.json()["order_id"])
    assert order.user_id is None

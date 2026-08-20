from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.app import (
    app,
    auth_service,
    cart_registry,
    product_catalog,
    wishlist_service,
)
from src.wishlist.service import WishlistService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    product_catalog.products.clear()
    cart_registry.carts.clear()
    wishlist_service.wishlists.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    product_catalog.products.clear()
    cart_registry.carts.clear()
    wishlist_service.wishlists.clear()


def auth_headers(name="Wishlist User", email="wishlist@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def test_wishlist_service_operations():
    service = WishlistService(product_catalog, cart_registry)
    p1 = product_catalog.add_product("Wireless Earbuds", 50.0, 10)
    p2 = product_catalog.add_product("Smartwatch", 200.0, 5)

    # Add items to wishlist
    service.add_item("user-1", p1)
    service.add_item("user-1", p2)

    # Adding duplicate does not create duplicate entries
    service.add_item("user-1", p1)

    user_products = service.get_user_wishlist_products("user-1")
    assert len(user_products) == 2
    assert user_products[0]["product_id"] == p1
    assert user_products[1]["product_id"] == p2

    # Move to cart
    cart_id = uuid4().hex
    cart = service.move_to_cart("user-1", p1, cart_id, quantity=2)
    assert cart.items[p1] == 2

    # Verify p1 is removed from wishlist
    remaining_products = service.get_user_wishlist_products("user-1")
    assert len(remaining_products) == 1
    assert remaining_products[0]["product_id"] == p2

    # Error when adding invalid product
    with pytest.raises(KeyError, match="product not found"):
        service.add_item("user-1", "non_existent_id")

    # Error when removing non-existent wishlist item
    with pytest.raises(KeyError, match="product not found in wishlist"):
        service.remove_item("user-1", p1)


def test_wishlist_endpoints_lifecycle():
    user, headers = auth_headers()
    p1 = product_catalog.add_product("Gaming Mouse", 60.0, 15)
    p2 = product_catalog.add_product("Mechanical Keyboard", 120.0, 8)

    # 1. Add item to wishlist (POST /wishlist/items/{product_id})
    res_add = client.post(f"/wishlist/items/{p1}", headers=headers)
    assert res_add.status_code == 201
    assert p1 in res_add.json()["product_ids"]

    client.post(f"/wishlist/items/{p2}", headers=headers)

    # 2. View my wishlist (GET /wishlist/me)
    res_list = client.get("/wishlist/me", headers=headers)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 2
    names = {item["name"] for item in items}
    assert "Gaming Mouse" in names
    assert "Mechanical Keyboard" in names

    # 3. Move item to cart (POST /wishlist/move-to-cart/{product_id})
    cart_id = uuid4().hex
    res_move = client.post(
        f"/wishlist/move-to-cart/{p1}",
        json={"cart_id": cart_id, "quantity": 1},
        headers=headers,
    )
    assert res_move.status_code == 200
    cart_items = res_move.json()["items"]
    assert any(item["product_id"] == p1 and item["quantity"] == 1 for item in cart_items)

    # Verify p1 is no longer in wishlist
    res_list2 = client.get("/wishlist/me", headers=headers)
    assert len(res_list2.json()) == 1

    # 4. Remove item from wishlist (DELETE /wishlist/items/{product_id})
    res_del = client.delete(f"/wishlist/items/{p2}", headers=headers)
    assert res_del.status_code == 204

    # Wishlist is now empty
    res_list3 = client.get("/wishlist/me", headers=headers)
    assert len(res_list3.json()) == 0


def test_wishlist_unauthenticated_and_error_handling():
    user, headers = auth_headers()
    p1 = product_catalog.add_product("Desk Lamp", 25.0, 5)

    # Unauthenticated calls
    assert client.post(f"/wishlist/items/{p1}").status_code == 401
    assert client.get("/wishlist/me").status_code == 401
    assert client.delete(f"/wishlist/items/{p1}").status_code == 401
    assert client.post(f"/wishlist/move-to-cart/{p1}", json={"cart_id": "c1"}).status_code == 401

    # 404 error when adding non-existent product
    assert client.post("/wishlist/items/fake_id", headers=headers).status_code == 404

    # 404 error when deleting item not in wishlist
    assert client.delete(f"/wishlist/items/{p1}", headers=headers).status_code == 404

    # 404 error when moving item not in wishlist to cart
    assert (
        client.post(
            f"/wishlist/move-to-cart/{p1}",
            json={"cart_id": "c1"},
            headers=headers,
        ).status_code
        == 404
    )

import pytest
from fastapi.testclient import TestClient

from src.app import app, cart_registry, order_manager, product_catalog
from src.shop.cart import CartRegistry
from src.shop.catalog import ProductCatalog
from src.shop.order import OrderManager

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_shop_state():
    product_catalog.products.clear()
    cart_registry.carts.clear()
    order_manager.orders.clear()
    yield
    product_catalog.products.clear()
    cart_registry.carts.clear()
    order_manager.orders.clear()


def test_product_catalog_adds_product():
    catalog = ProductCatalog()
    product_id = catalog.add_product("Keyboard", 50, 3)
    product = catalog.find_product(product_id)
    assert product.name == "Keyboard"
    assert product.price == 50
    assert product.stock == 3


@pytest.mark.parametrize(
    ("name", "price", "stock", "message"),
    [
        ("", 10, 1, "name must not be empty"),
        ("Item", -1, 1, "price must be a non-negative finite number"),
        ("Item", 10, -1, "stock must be non-negative"),
    ],
)
def test_product_validation(name, price, stock, message):
    catalog = ProductCatalog()
    with pytest.raises(ValueError, match=message):
        catalog.add_product(name, price, stock)


def test_cart_adds_and_removes_items_and_calculates_total():
    catalog = ProductCatalog()
    carts = CartRegistry(catalog)
    product_id = catalog.add_product("Keyboard", 50, 3)

    cart = carts.add_item("cart-1", product_id, 2)
    assert cart.items == {product_id: 2}
    assert carts.total(cart) == 100

    carts.remove_item("cart-1", product_id)
    assert cart.items == {}


def test_cart_checks_product_quantity_and_stock():
    catalog = ProductCatalog()
    carts = CartRegistry(catalog)
    product_id = catalog.add_product("Keyboard", 50, 2)

    with pytest.raises(ValueError, match="product not found"):
        carts.add_item("cart", "missing", 1)
    with pytest.raises(ValueError, match="quantity must be positive"):
        carts.add_item("cart", product_id, 0)
    with pytest.raises(ValueError, match="insufficient stock"):
        carts.add_item("cart", product_id, 3)


def test_order_checks_stock_then_decrements_it():
    catalog = ProductCatalog()
    carts = CartRegistry(catalog)
    orders = OrderManager(catalog, carts)
    product_id = catalog.add_product("Keyboard", 50, 3)
    carts.add_item("cart", product_id, 2)

    order_id = orders.create_order("cart")
    order = orders.find_order(order_id)
    assert order.cart_id == "cart"
    assert order.items == {product_id: 2}
    assert order.total == 100
    assert catalog.find_product(product_id).stock == 1
    assert carts.find_cart("cart").is_checked_out is True


def test_order_rejects_missing_empty_or_checked_out_cart():
    catalog = ProductCatalog()
    carts = CartRegistry(catalog)
    orders = OrderManager(catalog, carts)

    with pytest.raises(ValueError, match="cart not found"):
        orders.create_order("missing")

    carts.get_or_create("empty")
    with pytest.raises(ValueError, match="cart is empty"):
        orders.create_order("empty")

    product_id = catalog.add_product("Keyboard", 50, 1)
    carts.add_item("cart", product_id, 1)
    orders.create_order("cart")
    with pytest.raises(ValueError, match="cart has already been checked out"):
        orders.create_order("cart")


def test_shop_endpoint_lifecycle():
    product_response = client.post(
        "/products", json={"name": "Keyboard", "price": 50, "stock": 3}
    )
    assert product_response.status_code == 200
    product_id = product_response.json()["product_id"]

    add_response = client.post(
        "/carts/cart-1/items",
        json={"product_id": product_id, "quantity": 2},
    )
    assert add_response.status_code == 200
    assert add_response.json() == {
        "cart_id": "cart-1",
        "items": [
            {
                "product_id": product_id,
                "name": "Keyboard",
                "price": 50.0,
                "quantity": 2,
                "subtotal": 100.0,
            }
        ],
        "total": 100.0,
        "is_checked_out": False,
    }

    assert client.get("/carts/cart-1").json() == add_response.json()

    order_response = client.post("/orders", json={"cart_id": "cart-1"})
    assert order_response.status_code == 200
    assert order_response.json()["total"] == 100.0
    assert product_catalog.find_product(product_id).stock == 1


def test_remove_cart_item_endpoint():
    product_id = client.post(
        "/products", json={"name": "Mouse", "price": 20, "stock": 5}
    ).json()["product_id"]
    client.post(
        "/carts/cart/items", json={"product_id": product_id, "quantity": 1}
    )

    response = client.delete(f"/carts/cart/items/{product_id}")
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_get_missing_cart_returns_404():
    response = client.get("/carts/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Cart not found"}


@pytest.mark.parametrize(
    ("path", "payload", "message"),
    [
        ("/carts/cart/items", {"product_id": "missing", "quantity": 1}, "product not found"),
        ("/orders", {"cart_id": "missing"}, "cart not found"),
    ],
)
def test_shop_endpoints_return_400(path, payload, message):
    response = client.post(path, json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": message}


def test_endpoints_delegate_to_services(monkeypatch):
    product_calls = []
    cart_calls = []
    order_calls = []

    monkeypatch.setattr(
        product_catalog,
        "add_product",
        lambda name, price, stock: product_calls.append((name, price, stock))
        or "product-id",
    )
    response = client.post(
        "/products", json={"name": "Mouse", "price": 20, "stock": 5}
    )
    assert response.json() == {"product_id": "product-id"}
    assert product_calls == [("Mouse", 20.0, 5)]

    product_catalog.products["product-id"] = type(
        "ProductStub", (), {"name": "Mouse", "price": 20.0, "stock": 5}
    )()
    original_add = cart_registry.add_item

    def tracked_add(cart_id, product_id, quantity):
        cart_calls.append((cart_id, product_id, quantity))
        return original_add(cart_id, product_id, quantity)

    monkeypatch.setattr(cart_registry, "add_item", tracked_add)
    client.post(
        "/carts/cart/items", json={"product_id": "product-id", "quantity": 1}
    )
    assert cart_calls == [("cart", "product-id", 1)]

    class TimestampStub:
        @staticmethod
        def isoformat():
            return "2026-08-14T00:00:00+00:00"

    class OrderStub:
        order_id = "order-id"
        cart_id = "cart"
        items = {"product-id": 1}
        total = 20.0
        status = "pending"
        created_at = TimestampStub()
        updated_at = TimestampStub()

    monkeypatch.setattr(
        order_manager,
        "create_order",
        lambda cart_id: order_calls.append(cart_id) or "order-id",
    )
    monkeypatch.setattr(order_manager, "find_order", lambda order_id: OrderStub())
    response = client.post("/orders", json={"cart_id": "cart"})
    assert response.json()["order_id"] == "order-id"
    assert response.json()["total"] == 20.0
    assert order_calls == ["cart"]

import pytest
from fastapi.testclient import TestClient

from src.app import app, inventory_manager
from src.inventory.manager import InventoryManager

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_inventory():
    inventory_manager.products.clear()
    yield
    inventory_manager.products.clear()


def test_inventory_product_tracks_stock_history():
    manager = InventoryManager()
    product_id = manager.add_product("Keyboard", 10)

    product = manager.stock_in(product_id, 5)
    manager.stock_out(product_id, 4)

    assert product.stock == 11
    assert [movement.movement_type for movement in product.history] == [
        "initial",
        "stock_in",
        "stock_out",
    ]
    assert [movement.quantity for movement in product.history] == [10, 5, 4]
    assert [movement.stock_after for movement in product.history] == [10, 15, 11]


@pytest.mark.parametrize(
    ("name", "initial_stock", "message"),
    [
        ("", 0, "name must not be empty"),
        ("Keyboard", -1, "initial_stock must be non-negative"),
    ],
)
def test_inventory_product_validation(name, initial_stock, message):
    manager = InventoryManager()
    with pytest.raises(ValueError, match=message):
        manager.add_product(name, initial_stock)


@pytest.mark.parametrize("quantity", [0, -1])
def test_stock_in_rejects_non_positive_quantity(quantity):
    manager = InventoryManager()
    product_id = manager.add_product("Keyboard")
    with pytest.raises(ValueError, match="quantity must be positive"):
        manager.stock_in(product_id, quantity)


@pytest.mark.parametrize("quantity", [0, -1])
def test_stock_out_rejects_non_positive_quantity(quantity):
    manager = InventoryManager()
    product_id = manager.add_product("Keyboard", 10)
    with pytest.raises(ValueError, match="quantity must be positive"):
        manager.stock_out(product_id, quantity)


def test_stock_out_prevents_negative_stock_without_recording_history():
    manager = InventoryManager()
    product_id = manager.add_product("Keyboard", 2)
    product = manager.find_product(product_id)

    with pytest.raises(ValueError, match="insufficient stock"):
        manager.stock_out(product_id, 3)

    assert product.stock == 2
    assert len(product.history) == 1


@pytest.mark.parametrize("operation", ["stock_in", "stock_out"])
def test_stock_operations_reject_missing_product(operation):
    manager = InventoryManager()
    with pytest.raises(KeyError, match="product not found"):
        getattr(manager, operation)("missing", 1)


def test_inventory_endpoint_lifecycle_and_history():
    create_response = client.post(
        "/inventory/products",
        json={"name": "Keyboard", "initial_stock": 10},
    )
    assert create_response.status_code == 200
    product_id = create_response.json()["product_id"]
    assert create_response.json()["stock"] == 10

    stock_in_response = client.post(
        f"/inventory/{product_id}/stock-in", json={"quantity": 5}
    )
    assert stock_in_response.status_code == 200
    assert stock_in_response.json()["stock"] == 15

    stock_out_response = client.post(
        f"/inventory/{product_id}/stock-out", json={"quantity": 4}
    )
    assert stock_out_response.status_code == 200
    assert stock_out_response.json()["stock"] == 11

    inventory_response = client.get("/inventory")
    assert inventory_response.status_code == 200
    product = inventory_response.json()[0]
    assert product["product_id"] == product_id
    assert product["name"] == "Keyboard"
    assert product["stock"] == 11
    assert [entry["type"] for entry in product["history"]] == [
        "initial",
        "stock_in",
        "stock_out",
    ]
    assert [entry["stock_after"] for entry in product["history"]] == [
        10,
        15,
        11,
    ]
    assert all(entry["created_at"] for entry in product["history"])


def test_inventory_endpoints_prevent_invalid_stock_changes():
    product_id = client.post(
        "/inventory/products",
        json={"name": "Keyboard", "initial_stock": 2},
    ).json()["product_id"]

    response = client.post(
        f"/inventory/{product_id}/stock-out", json={"quantity": 3}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "insufficient stock"}
    assert inventory_manager.find_product(product_id).stock == 2

    response = client.post(
        f"/inventory/{product_id}/stock-in", json={"quantity": 0}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "quantity must be positive"}


@pytest.mark.parametrize("operation", ["stock-in", "stock-out"])
def test_inventory_endpoints_return_404_for_missing_product(operation):
    response = client.post(
        f"/inventory/missing/{operation}", json={"quantity": 1}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "product not found"}


def test_inventory_endpoints_delegate_to_manager(monkeypatch):
    calls = []

    original_add = inventory_manager.add_product
    original_stock_in = inventory_manager.stock_in
    original_stock_out = inventory_manager.stock_out

    def tracked_add(name, initial_stock):
        calls.append(("add_product", name, initial_stock))
        return original_add(name, initial_stock)

    def tracked_stock_in(product_id, quantity):
        calls.append(("stock_in", product_id, quantity))
        return original_stock_in(product_id, quantity)

    def tracked_stock_out(product_id, quantity):
        calls.append(("stock_out", product_id, quantity))
        return original_stock_out(product_id, quantity)

    monkeypatch.setattr(inventory_manager, "add_product", tracked_add)
    monkeypatch.setattr(inventory_manager, "stock_in", tracked_stock_in)
    monkeypatch.setattr(inventory_manager, "stock_out", tracked_stock_out)

    product_id = client.post(
        "/inventory/products",
        json={"name": "Mouse", "initial_stock": 5},
    ).json()["product_id"]
    client.post(f"/inventory/{product_id}/stock-in", json={"quantity": 2})
    client.post(f"/inventory/{product_id}/stock-out", json={"quantity": 1})

    assert calls == [
        ("add_product", "Mouse", 5),
        ("stock_in", product_id, 2),
        ("stock_out", product_id, 1),
    ]

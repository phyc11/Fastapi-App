import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service, shipping_service
from src.shipping.service import ShippingService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    shipping_service.user_addresses.clear()
    shipping_service.shipments.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    shipping_service.user_addresses.clear()
    shipping_service.shipments.clear()


def auth_headers(name="Shipping User", email="shipping@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def test_shipping_service_address_and_default_logic():
    service = ShippingService()

    # First address auto defaults to True
    addr1 = service.add_address("u1", "Alice", "0901234567", "123 Main St", "Hanoi", is_default=False)
    assert addr1.is_default is True

    # Second address non-default
    addr2 = service.add_address("u1", "Alice Work", "0907654321", "456 Office Rd", "Hanoi", is_default=False)
    assert addr2.is_default is False

    # Set addr2 as default
    updated2 = service.set_default_address("u1", addr2.address_id)
    assert updated2.is_default is True
    assert addr1.is_default is False

    # Error handling for missing address
    with pytest.raises(KeyError, match="address not found"):
        service.set_default_address("u1", "invalid_id")


def test_shipping_fee_calculation():
    service = ShippingService()

    # Standard 1kg fee
    fee1 = service.calculate_fee("Hanoi", weight_kg=1.0, order_amount=100.0)
    assert fee1["total_fee"] == 30.0
    assert fee1["free_shipping"] is False

    # Heavier 3kg fee (30 base + (2kg * 5) = 40)
    fee2 = service.calculate_fee("Hanoi", weight_kg=3.0, order_amount=100.0)
    assert fee2["total_fee"] == 40.0

    # Free shipping on high order amount (>= 500)
    fee3 = service.calculate_fee("Hanoi", weight_kg=10.0, order_amount=600.0)
    assert fee3["total_fee"] == 0.0
    assert fee3["free_shipping"] is True

    # Invalid weight
    with pytest.raises(ValueError, match="weight_kg must be positive"):
        service.calculate_fee("Hanoi", weight_kg=0.0)


def test_shipping_tracking_flow():
    service = ShippingService()

    shipment = service.register_shipment("TRACK123", "ORDER999", "FastShip")
    assert shipment.current_status == "preparing"

    updated = service.update_shipment_status("TRACK123", "picked_up", "Hub 1", "Courier picked up package")
    assert updated.current_status == "picked_up"
    assert len(updated.history) == 2

    # Track shipment
    tracked = service.track_shipment("TRACK123")
    assert tracked.tracking_number == "TRACK123"

    with pytest.raises(KeyError, match="tracking number not found"):
        service.track_shipment("MISSING_TRACK")


def test_shipping_endpoints_lifecycle():
    user, headers = auth_headers()

    # 1. Add Shipping Address (POST /shipping/addresses)
    res_add = client.post(
        "/shipping/addresses",
        json={
            "full_name": "Nguyen Van A",
            "phone": "0988888888",
            "street_address": "100 Le Loi",
            "city": "Da Nang",
            "is_default": True,
        },
        headers=headers,
    )
    assert res_add.status_code == 201
    addr1 = res_add.json()
    assert addr1["full_name"] == "Nguyen Van A"
    assert addr1["is_default"] is True
    addr1_id = addr1["address_id"]

    # Add second address
    res_add2 = client.post(
        "/shipping/addresses",
        json={
            "full_name": "Nguyen Van A Office",
            "phone": "0977777777",
            "street_address": "200 Tran Phu",
            "city": "Da Nang",
            "is_default": True,  # should make addr2 default and unmark addr1
        },
        headers=headers,
    )
    assert res_add2.status_code == 201
    addr2_id = res_add2.json()["address_id"]

    # 2. Get User Addresses (GET /shipping/addresses/me)
    res_list = client.get("/shipping/addresses/me", headers=headers)
    assert res_list.status_code == 200
    addresses = res_list.json()
    assert len(addresses) == 2

    # 3. Set Default Address (PUT /shipping/addresses/{address_id}/default)
    res_def = client.put(f"/shipping/addresses/{addr1_id}/default", headers=headers)
    assert res_def.status_code == 200
    assert res_def.json()["is_default"] is True

    # 4. Calculate Fee (POST /shipping/calculate-fee)
    res_fee = client.post(
        "/shipping/calculate-fee",
        json={"city": "Da Nang", "weight_kg": 2.5, "order_amount": 150.0},
    )
    assert res_fee.status_code == 200
    assert res_fee.json()["total_fee"] == 37.5

    # 5. Track Shipment (GET /shipping/track/{tracking_number})
    # Register shipment in service first
    shipping_service.register_shipment("EXPRESS888", "ORD-1234", "GHTK")

    res_track = client.get("/shipping/track/EXPRESS888")
    assert res_track.status_code == 200
    track_data = res_track.json()
    assert track_data["tracking_number"] == "EXPRESS888"
    assert track_data["carrier"] == "GHTK"


def test_shipping_endpoints_unauthenticated_and_errors():
    user, headers = auth_headers()

    # Unauthenticated requests return 401
    assert client.post("/shipping/addresses", json={"full_name": "a", "phone": "p", "street_address": "s", "city": "c"}).status_code == 401
    assert client.get("/shipping/addresses/me").status_code == 401
    assert client.put("/shipping/addresses/fake_id/default").status_code == 401

    # 404 for setting default on missing address
    assert client.put("/shipping/addresses/missing_id/default", headers=headers).status_code == 404

    # 404 for tracking missing shipment
    assert client.get("/shipping/track/NON_EXISTENT").status_code == 404

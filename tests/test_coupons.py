from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service, coupon_service
from src.coupons.service import Coupon, CouponService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    coupon_service.coupons.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    coupon_service.coupons.clear()


def auth_headers(name="Admin User", email="admin@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def test_coupon_service_creation_and_validation():
    service = CouponService()
    coupon = service.create_coupon(
        code="SAVE20",
        discount_type="percentage",
        discount_value=20.0,
        min_order_value=50.0,
        max_discount_amount=30.0,
    )

    assert coupon.code == "SAVE20"
    assert coupon.discount_type == "percentage"
    assert coupon.discount_value == 20.0
    assert coupon.min_order_value == 50.0

    # Validate under min_order_value
    val_res = service.validate_coupon("SAVE20", order_amount=40.0)
    assert not val_res["is_valid"]
    assert "Minimum order value" in val_res["reason"]

    # Validate valid order
    val_res = service.validate_coupon("SAVE20", order_amount=100.0)
    assert val_res["is_valid"]
    assert val_res["discount_amount"] == 20.0
    assert val_res["final_amount"] == 80.0

    # Validate capped discount
    val_res = service.validate_coupon("SAVE20", order_amount=200.0)
    assert val_res["is_valid"]
    assert val_res["discount_amount"] == 30.0
    assert val_res["final_amount"] == 170.0


def test_coupon_service_fixed_amount_discount():
    service = CouponService()
    service.create_coupon(
        code="FLAT50",
        discount_type="fixed_amount",
        discount_value=50.0,
        min_order_value=100.0,
    )

    val_res = service.validate_coupon("FLAT50", order_amount=150.0)
    assert val_res["is_valid"]
    assert val_res["discount_amount"] == 50.0
    assert val_res["final_amount"] == 100.0

    # Discount capped by order amount if order < discount
    service.create_coupon(
        code="FLAT100",
        discount_type="fixed_amount",
        discount_value=100.0,
    )
    val_res = service.validate_coupon("FLAT100", order_amount=30.0)
    assert val_res["is_valid"]
    assert val_res["discount_amount"] == 30.0
    assert val_res["final_amount"] == 0.0


def test_coupon_validation_errors():
    service = CouponService()

    with pytest.raises(ValueError, match="code must not be empty"):
        service.create_coupon("", "percentage", 10.0)

    with pytest.raises(ValueError, match="discount_type must be"):
        service.create_coupon("CODE", "invalid_type", 10.0)

    with pytest.raises(ValueError, match="discount_value must be positive"):
        service.create_coupon("CODE", "percentage", -5.0)

    with pytest.raises(ValueError, match="percentage discount_value cannot exceed 100"):
        service.create_coupon("CODE", "percentage", 150.0)

    service.create_coupon("EXISTS", "percentage", 10.0)
    with pytest.raises(ValueError, match="already exists"):
        service.create_coupon("exists", "percentage", 10.0)


def test_coupon_expiration_and_max_uses():
    service = CouponService()
    past_time = datetime.now(timezone.utc) - timedelta(days=1)
    future_time = datetime.now(timezone.utc) + timedelta(days=1)

    # Cannot create coupon with past expiration
    with pytest.raises(ValueError, match="expires_at must be in the future"):
        service.create_coupon("PAST", "percentage", 10.0, expires_at=past_time)

    coupon = service.create_coupon(
        "LIMITED", "percentage", 10.0, max_uses=2, expires_at=future_time
    )

    # Active coupons list
    active = service.list_active_coupons()
    assert len(active) == 1
    assert active[0].code == "LIMITED"

    # Simulate usage
    coupon.increment_usage()
    coupon.increment_usage()
    val_res = service.validate_coupon("LIMITED", 100.0)
    assert not val_res["is_valid"]
    assert "usage limit reached" in val_res["reason"]

    # Active coupons excludes exhausted
    assert len(service.list_active_coupons()) == 0


def test_coupon_endpoints_lifecycle():
    _, headers = auth_headers()

    # 1. Create Coupon (POST /coupons)
    response = client.post(
        "/coupons",
        json={
            "code": "WELCOME10",
            "discount_type": "percentage",
            "discount_value": 10.0,
            "min_order_value": 20.0,
        },
        headers=headers,
    )
    assert response.status_code == 201
    created = response.json()
    assert created["code"] == "WELCOME10"
    assert created["discount_type"] == "percentage"
    assert created["discount_value"] == 10.0
    assert created["min_order_value"] == 20.0
    assert created["is_active"] is True

    # 2. List Active Coupons (GET /coupons/active)
    list_res = client.get("/coupons/active")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["code"] == "WELCOME10"

    # 3. Validate Coupon (POST /coupons/validate)
    val_res = client.post(
        "/coupons/validate",
        json={"code": "welcome10", "order_amount": 50.0},
    )
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is True
    assert val_data["discount_amount"] == 5.0
    assert val_data["final_amount"] == 45.0

    # 4. Deactivate Coupon (DELETE /coupons/{code})
    del_res = client.delete("/coupons/WELCOME10", headers=headers)
    assert del_res.status_code == 204

    # Check that it's no longer active
    list_res2 = client.get("/coupons/active")
    assert len(list_res2.json()) == 0


def test_coupon_endpoints_authentication():
    # POST and DELETE require auth
    assert client.post(
        "/coupons",
        json={"code": "NOAUTH", "discount_type": "fixed_amount", "discount_value": 10},
    ).status_code == 401

    assert client.delete("/coupons/NOAUTH").status_code == 401

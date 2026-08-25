import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service, coupon_service, reward_service
from src.rewards.service import RewardService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    coupon_service.coupons.clear()
    reward_service.accounts.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    coupon_service.coupons.clear()
    reward_service.accounts.clear()


def auth_headers(name="Reward User", email="reward@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def test_reward_service_earning_and_tier_progression():
    service = RewardService(coupon_service)

    # Initial Bronze tier
    tier0 = service.calculate_tier(0)
    assert tier0["tier"] == "Bronze"
    assert tier0["multiplier"] == 1.0
    assert tier0["next_tier"] == "Silver"
    assert tier0["points_to_next_tier"] == 200

    # Earn 100 points
    service.earn_points("u1", amount_spent=100.0)
    acc1 = service.get_user_account("u1")
    assert acc1.points_balance == 100
    assert acc1.lifetime_points == 100

    # Earn more to reach Silver tier (>= 200)
    service.earn_points("u1", amount_spent=100.0)  # +100 = 200 points
    tier_silver = service.calculate_tier(acc1.lifetime_points)
    assert tier_silver["tier"] == "Silver"
    assert tier_silver["multiplier"] == 1.2

    # Earn at Silver tier (multiplier 1.2x on $100 -> 120 points)
    tx = service.earn_points("u1", amount_spent=100.0)
    assert tx.points == 120
    assert acc1.points_balance == 320


def test_reward_service_redemption():
    service = RewardService(coupon_service)
    service.add_bonus_points("u2", points=200)

    res = service.redeem_points("u2", points_to_redeem=100)
    assert res["discount_amount"] == 10.0
    assert res["points_redeemed"] == 100
    assert res["remaining_points"] == 100
    assert res["voucher_code"].startswith("RW-")

    # Verify coupon created in CouponService
    coupon = coupon_service.get_coupon(res["voucher_code"])
    assert coupon is not None
    assert coupon.discount_value == 10.0

    # Insufficient points error
    with pytest.raises(ValueError, match="insufficient points balance"):
        service.redeem_points("u2", points_to_redeem=500)

    # Below minimum redemption points error
    with pytest.raises(ValueError, match="minimum redemption is 50 points"):
        service.redeem_points("u2", points_to_redeem=20)


def test_rewards_endpoints_lifecycle():
    user, headers = auth_headers()

    # 1. Get Tiers (Public) (GET /rewards/tiers)
    tiers_res = client.get("/rewards/tiers")
    assert tiers_res.status_code == 200
    tiers_list = tiers_res.json()
    assert len(tiers_list) == 4
    assert tiers_list[0]["tier"] == "Bronze"

    # 2. Get My Rewards Info (GET /rewards/me)
    me_res = client.get("/rewards/me", headers=headers)
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["tier"] == "Bronze"
    assert data["points_balance"] == 0

    # Add bonus points directly in service to test redeem API
    reward_service.add_bonus_points(user.user_id, 300)

    # 3. Redeem Points (POST /rewards/redeem)
    redeem_res = client.post(
        "/rewards/redeem",
        json={"points": 100},
        headers=headers,
    )
    assert redeem_res.status_code == 200
    redeem_data = redeem_res.json()
    assert redeem_data["discount_amount"] == 10.0
    assert redeem_data["remaining_points"] == 200


def test_rewards_endpoints_unauthenticated_and_errors():
    user, headers = auth_headers()

    # 401 Unauthenticated
    assert client.get("/rewards/me").status_code == 401
    assert client.post("/rewards/redeem", json={"points": 100}).status_code == 401

    # 400 Bad request (insufficient points)
    assert client.post("/rewards/redeem", json={"points": 100}, headers=headers).status_code == 400

from datetime import datetime, timezone
from uuid import uuid4

from src.coupons.service import CouponService

TIER_CONFIGS = [
    {
        "tier": "Bronze",
        "min_points": 0,
        "max_points": 199,
        "multiplier": 1.0,
        "benefits": ["Earn 1x reward points on all purchases"],
    },
    {
        "tier": "Silver",
        "min_points": 200,
        "max_points": 499,
        "multiplier": 1.2,
        "benefits": [
            "Earn 1.2x reward points on all purchases",
            "5% Birthday discount voucher",
        ],
    },
    {
        "tier": "Gold",
        "min_points": 500,
        "max_points": 999,
        "multiplier": 1.5,
        "benefits": [
            "Earn 1.5x reward points on all purchases",
            "10% Birthday discount voucher",
            "Free standard shipping",
        ],
    },
    {
        "tier": "Platinum",
        "min_points": 1000,
        "max_points": None,
        "multiplier": 2.0,
        "benefits": [
            "Earn 2.0x reward points on all purchases",
            "15% Birthday discount voucher",
            "Free express shipping",
            "Priority customer support",
        ],
    },
]


class RewardTransaction:
    def __init__(
        self,
        user_id: str,
        type: str,
        points: int,
        description: str,
        timestamp: datetime | None = None,
    ) -> None:
        type_key = type.strip().upper()
        if type_key not in {"EARN", "REDEEM", "BONUS"}:
            raise ValueError("type must be EARN, REDEEM, or BONUS")

        self.transaction_id = uuid4().hex
        self.user_id = user_id
        self.type = type_key
        self.points = points
        self.description = description.strip()
        self.timestamp = timestamp or datetime.now(timezone.utc)


class UserRewardAccount:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.points_balance = 0
        self.lifetime_points = 0
        self.transactions: list[RewardTransaction] = []


class RewardService:
    def __init__(self, coupon_service: CouponService | None = None) -> None:
        self.coupon_service = coupon_service
        self.accounts: dict[str, UserRewardAccount] = {}

    def get_user_account(self, user_id: str) -> UserRewardAccount:
        account = self.accounts.get(user_id)
        if account is None:
            account = UserRewardAccount(user_id)
            self.accounts[user_id] = account
        return account

    def calculate_tier(self, lifetime_points: int) -> dict:
        current_tier = TIER_CONFIGS[0]
        for config in TIER_CONFIGS:
            if lifetime_points >= config["min_points"]:
                current_tier = config

        next_tier = None
        points_to_next_tier = 0
        for config in TIER_CONFIGS:
            if config["min_points"] > lifetime_points:
                next_tier = config["tier"]
                points_to_next_tier = config["min_points"] - lifetime_points
                break

        return {
            "tier": current_tier["tier"],
            "multiplier": current_tier["multiplier"],
            "benefits": current_tier["benefits"],
            "next_tier": next_tier,
            "points_to_next_tier": points_to_next_tier,
        }

    def get_tier_benefits(self) -> list[dict]:
        return TIER_CONFIGS

    def earn_points(
        self, user_id: str, amount_spent: float, description: str = "Purchase reward"
    ) -> RewardTransaction:
        if amount_spent <= 0:
            raise ValueError("amount_spent must be positive")

        account = self.get_user_account(user_id)
        tier_info = self.calculate_tier(account.lifetime_points)
        earned_points = int(amount_spent * tier_info["multiplier"])

        account.points_balance += earned_points
        account.lifetime_points += earned_points

        tx = RewardTransaction(
            user_id=user_id,
            type="EARN",
            points=earned_points,
            description=description,
        )
        account.transactions.append(tx)
        return tx

    def add_bonus_points(
        self, user_id: str, points: int, description: str = "Bonus points"
    ) -> RewardTransaction:
        if points <= 0:
            raise ValueError("points must be positive")

        account = self.get_user_account(user_id)
        account.points_balance += points
        account.lifetime_points += points

        tx = RewardTransaction(
            user_id=user_id,
            type="BONUS",
            points=points,
            description=description,
        )
        account.transactions.append(tx)
        return tx

    def redeem_points(self, user_id: str, points_to_redeem: int) -> dict:
        if points_to_redeem < 50:
            raise ValueError("minimum redemption is 50 points")

        account = self.get_user_account(user_id)
        if account.points_balance < points_to_redeem:
            raise ValueError("insufficient points balance")

        # 10 points = $1.00 discount
        discount_amount = round(points_to_redeem / 10.0, 2)
        code = f"RW-{uuid4().hex[:8].upper()}"

        account.points_balance -= points_to_redeem
        tx = RewardTransaction(
            user_id=user_id,
            type="REDEEM",
            points=-points_to_redeem,
            description=f"Redeemed for ${discount_amount} voucher ({code})",
        )
        account.transactions.append(tx)

        if self.coupon_service:
            self.coupon_service.create_coupon(
                code=code,
                discount_type="fixed_amount",
                discount_value=discount_amount,
                max_uses=1,
            )

        return {
            "voucher_code": code,
            "discount_amount": discount_amount,
            "points_redeemed": points_to_redeem,
            "remaining_points": account.points_balance,
        }

from datetime import datetime, timezone
from uuid import uuid4

VALID_DISCOUNT_TYPES = {"percentage", "fixed_amount"}


class Coupon:
    def __init__(
        self,
        code: str,
        discount_type: str,
        discount_value: float,
        min_order_value: float = 0.0,
        max_discount_amount: float | None = None,
        max_uses: int | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        normalized_code = code.strip().upper()
        if not normalized_code:
            raise ValueError("code must not be empty")

        if discount_type not in VALID_DISCOUNT_TYPES:
            raise ValueError("discount_type must be 'percentage' or 'fixed_amount'")

        if discount_value <= 0:
            raise ValueError("discount_value must be positive")

        if discount_type == "percentage" and discount_value > 100:
            raise ValueError("percentage discount_value cannot exceed 100")

        if min_order_value < 0:
            raise ValueError("min_order_value must be non-negative")

        if max_discount_amount is not None and max_discount_amount < 0:
            raise ValueError("max_discount_amount must be non-negative")

        if max_uses is not None and max_uses <= 0:
            raise ValueError("max_uses must be a positive integer")

        now = datetime.now(timezone.utc)
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now:
                raise ValueError("expires_at must be in the future")

        self.coupon_id = uuid4().hex
        self.code = normalized_code
        self.discount_type = discount_type
        self.discount_value = float(discount_value)
        self.min_order_value = float(min_order_value)
        self.max_discount_amount = (
            float(max_discount_amount) if max_discount_amount is not None else None
        )
        self.max_uses = max_uses
        self.uses_count = 0
        self.expires_at = expires_at
        self.is_active = True
        self.created_at = now

    def is_valid(
        self, order_amount: float, now: datetime | None = None
    ) -> tuple[bool, str]:
        if not self.is_active:
            return False, "Coupon is inactive"

        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if self.expires_at is not None and current_time >= self.expires_at:
            return False, "Coupon has expired"

        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False, "Coupon usage limit reached"

        if order_amount < self.min_order_value:
            return (
                False,
                f"Minimum order value of {self.min_order_value} required",
            )

        return True, "Coupon is valid"

    def calculate_discount(self, order_amount: float) -> float:
        if order_amount <= 0:
            return 0.0

        if self.discount_type == "percentage":
            discount = order_amount * (self.discount_value / 100.0)
            if self.max_discount_amount is not None:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.discount_value

        # Discount cannot exceed order amount
        return round(min(discount, order_amount), 2)

    def increment_usage(self) -> None:
        self.uses_count += 1


class CouponService:
    def __init__(self) -> None:
        self.coupons: dict[str, Coupon] = {}

    def create_coupon(
        self,
        code: str,
        discount_type: str,
        discount_value: float,
        min_order_value: float = 0.0,
        max_discount_amount: float | None = None,
        max_uses: int | None = None,
        expires_at: datetime | None = None,
    ) -> Coupon:
        normalized_code = code.strip().upper()
        if normalized_code in self.coupons:
            raise ValueError(f"Coupon with code '{normalized_code}' already exists")

        coupon = Coupon(
            code=normalized_code,
            discount_type=discount_type,
            discount_value=discount_value,
            min_order_value=min_order_value,
            max_discount_amount=max_discount_amount,
            max_uses=max_uses,
            expires_at=expires_at,
        )
        self.coupons[normalized_code] = coupon
        return coupon

    def get_coupon(self, code: str) -> Coupon | None:
        return self.coupons.get(code.strip().upper())

    def list_active_coupons(self, now: datetime | None = None) -> list[Coupon]:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        active_list = []
        for coupon in self.coupons.values():
            if not coupon.is_active:
                continue
            if coupon.expires_at is not None and current_time >= coupon.expires_at:
                continue
            if coupon.max_uses is not None and coupon.uses_count >= coupon.max_uses:
                continue
            active_list.append(coupon)
        return active_list

    def validate_coupon(
        self, code: str, order_amount: float, now: datetime | None = None
    ) -> dict:
        coupon = self.get_coupon(code)
        if coupon is None:
            return {
                "is_valid": False,
                "code": code.strip().upper(),
                "discount_amount": 0.0,
                "final_amount": round(order_amount, 2),
                "reason": "Coupon not found",
            }

        is_valid, reason = coupon.is_valid(order_amount, now=now)
        if not is_valid:
            return {
                "is_valid": False,
                "code": coupon.code,
                "discount_amount": 0.0,
                "final_amount": round(order_amount, 2),
                "reason": reason,
            }

        discount_amount = coupon.calculate_discount(order_amount)
        final_amount = round(max(0.0, order_amount - discount_amount), 2)
        return {
            "is_valid": True,
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
            "discount_amount": discount_amount,
            "final_amount": final_amount,
            "reason": None,
        }

    def deactivate_coupon(self, code: str) -> Coupon:
        coupon = self.get_coupon(code)
        if coupon is None:
            raise KeyError(f"Coupon '{code.strip().upper()}' not found")
        coupon.is_active = False
        return coupon

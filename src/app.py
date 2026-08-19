import os
from datetime import date, datetime
from math import isfinite, isqrt, sqrt
from uuid import uuid4

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.analytics.service import AnalyticsService
from src.auth.service import AuthService, User
from src.bank_account import BankAccount, account_registry
from src.coupons.service import Coupon, CouponService
from src.expense_tracker.tracker import ExpenseTracker
from src.inventory.manager import InventoryManager
from src.library.book import Catalog
from src.library.loan import LoanManager
from src.library.member import MemberRegistry
from src.notifications.service import Notification, NotificationService
from src.reviews.service import Review, ReviewService
from src.shop.cart import CartRegistry
from src.shop.catalog import ProductCatalog
from src.shop.order import OrderManager
from src.uploads.service import ImageStorage, StoredImage

app = FastAPI()

auth_service = AuthService()
notification_service = NotificationService()
image_storage = ImageStorage()
bearer_scheme = HTTPBearer(auto_error=False)

inventory_manager = InventoryManager()
catalog = Catalog()
member_registry = MemberRegistry()
loan_manager = LoanManager(catalog, member_registry)
product_catalog = ProductCatalog()
cart_registry = CartRegistry(product_catalog)
order_manager = OrderManager(product_catalog, cart_registry)
coupon_service = CouponService()
analytics_service = AnalyticsService(
    order_manager, product_catalog, inventory_manager, auth_service
)


class RegisterUserRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class CreateNotificationRequest(BaseModel):
    type: str
    message: str


class ReviewRequest(BaseModel):
    rating: int
    comment: str = ""


class CreateAccountRequest(BaseModel):
    initial_balance: float = 0


class AccountTransactionRequest(BaseModel):
    amount: float


class AddBookRequest(BaseModel):
    title: str
    author: str


class RegisterMemberRequest(BaseModel):
    name: str
    email: str


class BorrowBookRequest(BaseModel):
    book_id: str
    member_id: str


class CreateProductRequest(BaseModel):
    name: str
    price: float
    stock: int


class CreateInventoryProductRequest(BaseModel):
    name: str
    initial_stock: int = 0


class StockMovementRequest(BaseModel):
    quantity: int


class AddCartItemRequest(BaseModel):
    product_id: str
    quantity: int


class CreateOrderRequest(BaseModel):
    cart_id: str


class CreateTransactionRequest(BaseModel):
    type: str
    amount: float
    category: str
    occurred_on: date | None = None
    description: str = ""


class CreateCouponRequest(BaseModel):
    code: str
    discount_type: str
    discount_value: float
    min_order_value: float = 0.0
    max_discount_amount: float | None = None
    max_uses: int | None = None
    expires_at: datetime | None = None


class ValidateCouponRequest(BaseModel):
    code: str
    order_amount: float


def add(a: int, b: int) -> int:
    return a + b


def increment(a: int) -> int:
    return a + 1


def subtract(a: int, b: int) -> int:
    return a - b


def multiply(a: int, b: int) -> int:
    return a * b


def divide(a: int, b: int) -> float:
    return a / b


def modulo(a: int, b: int) -> int:
    return a % b


def average(a: int, b: int) -> float:
    return add(a, b) / 2


def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")

    current, following = 0, 1
    for _ in range(n):
        current, following = following, current + following
    return current

def mean(numbers: list[int | float]) -> float:
    if not numbers:
        raise ValueError("numbers must not be empty")
    return sum(numbers) / len(numbers)


def median(numbers: list[int | float]) -> int | float:
    if not numbers:
        raise ValueError("numbers must not be empty")

    sorted_numbers = sorted(numbers)
    midpoint = len(sorted_numbers) // 2
    if len(sorted_numbers) % 2:
        return sorted_numbers[midpoint]
    return (sorted_numbers[midpoint - 1] + sorted_numbers[midpoint]) / 2


def stddev(numbers: list[int | float]) -> float:
    average_value = mean(numbers)
    variance = sum((number - average_value) ** 2 for number in numbers) / len(numbers)
    return sqrt(variance)

def gcd(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def lcm(a: int, b: int) -> int:
    divisor = gcd(a, b)
    if divisor == 0:
        return 0
    return abs(a * b) // divisor

def is_prime(n: int) -> bool:
    if n < 2:
        raise ValueError("n must be at least 2")
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    return all(n % divisor != 0 for divisor in range(3, isqrt(n) + 1, 2))

def reverse_string(s: str) -> str:
    return s[::-1]


def is_palindrome(s: str) -> bool:
    normalized = s.lower().replace(" ", "")
    return normalized == reverse_string(normalized)

def celsius_to_fahrenheit(c: int | float) -> float:
    return c * 9 / 5 + 32


def fahrenheit_to_celsius(f: int | float) -> float:
    return (f - 32) * 5 / 9

def sort_numbers(numbers: list[int | float]) -> list[int | float]:
    result = numbers.copy()
    for index in range(1, len(result)):
        current = result[index]
        position = index - 1
        while position >= 0 and result[position] > current:
            result[position + 1] = result[position]
            position -= 1
        result[position + 1] = current
    return result

def clamp(
    value: int | float,
    min_value: int | float,
    max_value: int | float,
) -> int | float:
    if min_value > max_value:
        raise ValueError("min_value must be less than or equal to max_value")
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value

def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")

    result = 1
    for factor in range(2, n + 1):
        result *= factor
    return result

def reverse_list(items: list) -> list:
    result = []
    for index in range(len(items) - 1, -1, -1):
        result.append(items[index])
    return result

def word_count(text: str) -> int:
    return len(text.split())

def is_leap_year(year: int) -> bool:
    return year % 400 == 0 or (year % 4 == 0 and year % 100 != 0)

def to_binary(n: int) -> str:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return "0"

    result = ""
    while n:
        result = str(n % 2) + result
        n //= 2
    return result

def count_vowels(text: str) -> int:
    return sum(character.lower() in "aeiou" for character in text)

def is_anagram(a: str, b: str) -> bool:
    normalized_a = a.lower().replace(" ", "")
    normalized_b = b.lower().replace(" ", "")
    if len(normalized_a) != len(normalized_b):
        return False

    frequencies = {}
    for character in normalized_a:
        frequencies[character] = frequencies.get(character, 0) + 1

    for character in normalized_b:
        if frequencies.get(character, 0) == 0:
            return False
        frequencies[character] -= 1
    return True

def compound_interest(
    principal: int | float,
    rate: int | float,
    years: int | float,
) -> float:
    if principal < 0:
        raise ValueError("principal must be non-negative")
    if years < 0:
        raise ValueError("years must be non-negative")
    return principal * (1 + rate) ** years

def calculate_bmi(weight: int | float, height: int | float) -> float:
    if not isfinite(weight) or weight <= 0:
        raise ValueError("weight must be a positive finite number")
    if not isfinite(height) or height <= 0:
        raise ValueError("height must be a positive finite number")
    return weight / height**2


def classify_bmi(bmi_value: int | float) -> str:
    if bmi_value < 18.5:
        return "underweight"
    if bmi_value < 25:
        return "normal"
    if bmi_value < 30:
        return "overweight"
    return "obese"

def greet(name: str) -> str:
    return f"Hello, {name}!"


def power(a: int, b: int) -> int:
    if b < 0:
        raise ValueError("Exponent must be non-negative")
    return a ** b


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return auth_service.get_user_from_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

def _serialize_image(image: StoredImage):
    result = {
        "image_id": image.image_id,
        "filename": image.filename,
        "content_type": image.content_type,
        "size": image.size,
        "created_at": image.created_at.isoformat(),
    }
    if image.product_id is not None:
        result["product_id"] = image.product_id
    return result


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read()
    await file.close()
    return content


@app.post("/users/me/avatar", status_code=201)
async def upload_avatar_endpoint(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    try:
        image = image_storage.save_avatar(
            current_user.user_id,
            file.filename or "avatar",
            file.content_type or "",
            await _read_upload(file),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_image(image)


@app.post("/products/{product_id}/images", status_code=201)
async def upload_product_image_endpoint(
    product_id: str,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    if product_catalog.find_product(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        image = image_storage.save_product_image(
            product_id,
            current_user.user_id,
            file.filename or "product-image",
            file.content_type or "",
            await _read_upload(file),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_image(image)


@app.delete("/products/{product_id}/images/{image_id}", status_code=204)
def delete_product_image_endpoint(
    product_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
):
    if product_catalog.find_product(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        image_storage.delete_product_image(
            product_id, image_id, current_user.user_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _serialize_notification(notification: Notification):
    return {
        "notification_id": notification.notification_id,
        "type": notification.notification_type,
        "message": notification.message,
        "status": notification.status,
        "created_at": notification.created_at.isoformat(),
        "updated_at": notification.updated_at.isoformat(),
    }


def _serialize_user(user: User):
    return {"user_id": user.user_id, "name": user.name, "email": user.email}



@app.post("/notifications", status_code=201)
def create_notification_endpoint(
    payload: CreateNotificationRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        notification = notification_service.create(
            current_user.user_id, payload.type, payload.message
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_notification(notification)


@app.get("/notifications/me")
def list_my_notifications_endpoint(
    current_user: User = Depends(get_current_user),
):
    return [
        _serialize_notification(notification)
        for notification in notification_service.list_for_user(
            current_user.user_id
        )
    ]


@app.patch("/notifications/{notification_id}/read")
def mark_notification_read_endpoint(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        notification = notification_service.mark_read(
            notification_id, current_user.user_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    return _serialize_notification(notification)

@app.post("/auth/register", status_code=201)
def register_user_endpoint(payload: RegisterUserRequest):
    try:
        user = auth_service.register(payload.name, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_user(user)


def _serialize_session(session):
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "last_used_at": session.last_used_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "is_active": session.is_active,
        "revoked_at": (
            session.revoked_at.isoformat()
            if session.revoked_at is not None
            else None
        ),
    }


@app.post("/auth/login")
def login_endpoint(payload: LoginRequest):
    try:
        user = auth_service.authenticate(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    access_token, refresh_token = auth_service.create_session(user)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": auth_service.access_token_minutes * 60,
    }


@app.post("/auth/refresh")
def refresh_token_endpoint(payload: RefreshTokenRequest):
    try:
        access_token, refresh_token = auth_service.refresh(
            payload.refresh_token
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": auth_service.access_token_minutes * 60,
    }


@app.post("/auth/logout", status_code=204)
def logout_endpoint(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    auth_service.revoke_access_token(credentials.credentials)


@app.get("/auth/sessions")
def list_sessions_endpoint(current_user: User = Depends(get_current_user)):
    return [
        _serialize_session(session)
        for session in auth_service.list_sessions(current_user.user_id)
    ]


@app.get("/users/me")
def get_current_user_endpoint(current_user: User = Depends(get_current_user)):
    return _serialize_user(current_user)


review_service = ReviewService(product_catalog, mean)
expense_tracker = ExpenseTracker(mean, sort_numbers)


def _serialize_review(review: Review):
    return {
        "review_id": review.review_id,
        "product_id": review.product_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat(),
        "updated_at": review.updated_at.isoformat(),
    }


@app.post("/products/{product_id}/reviews", status_code=201)
def create_review_endpoint(
    product_id: str,
    payload: ReviewRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        review = review_service.create(
            product_id,
            current_user.user_id,
            payload.rating,
            payload.comment,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_review(review)


@app.get("/products/{product_id}/reviews")
def list_product_reviews_endpoint(product_id: str):
    try:
        reviews = review_service.list_for_product(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    return [_serialize_review(review) for review in reviews]


@app.patch("/products/{product_id}/reviews/me")
def update_my_review_endpoint(
    product_id: str,
    payload: ReviewRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        review = review_service.update_mine(
            product_id,
            current_user.user_id,
            payload.rating,
            payload.comment,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_review(review)


@app.delete("/products/{product_id}/reviews/me", status_code=204)
def delete_my_review_endpoint(
    product_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        review_service.delete_mine(product_id, current_user.user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@app.get("/products/{product_id}/rating")
def product_rating_endpoint(product_id: str):
    try:
        average_rating, review_count = review_service.rating_summary(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    return {
        "product_id": product_id,
        "average_rating": (
            round(average_rating, 2) if average_rating is not None else None
        ),
        "review_count": review_count,
    }


def _serialize_transaction(transaction_id, transaction):
    return {
        "transaction_id": transaction_id,
        "type": transaction.transaction_type,
        "amount": transaction.amount,
        "category": transaction.category,
        "occurred_on": transaction.occurred_on.isoformat(),
        "description": transaction.description,
    }


@app.post("/transactions")
def create_transaction_endpoint(payload: CreateTransactionRequest):
    try:
        transaction_id = expense_tracker.add_transaction(
            payload.type,
            payload.amount,
            payload.category,
            payload.occurred_on or date.today(),
            payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    transaction = expense_tracker.transactions[transaction_id]
    return _serialize_transaction(transaction_id, transaction)


@app.get("/transactions")
def list_transactions_endpoint():
    return [
        _serialize_transaction(transaction_id, transaction)
        for transaction_id, transaction in expense_tracker.list_transactions()
    ]


@app.get("/reports/monthly")
def monthly_report_endpoint():
    return expense_tracker.monthly_report()


@app.get("/reports/categories")
def category_report_endpoint():
    return expense_tracker.category_report()

def _serialize_inventory_product(product_id, product):
    return {
        "product_id": product_id,
        "name": product.name,
        "stock": product.stock,
        "history": [
            {
                "movement_id": movement.movement_id,
                "type": movement.movement_type,
                "quantity": movement.quantity,
                "stock_after": movement.stock_after,
                "created_at": movement.created_at.isoformat(),
            }
            for movement in product.history
        ],
    }


@app.post("/inventory/products")
def create_inventory_product_endpoint(payload: CreateInventoryProductRequest):
    try:
        product_id = inventory_manager.add_product(
            payload.name, payload.initial_stock
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    product = inventory_manager.find_product(product_id)
    return _serialize_inventory_product(product_id, product)


@app.post("/inventory/{product_id}/stock-in")
def stock_in_endpoint(product_id: str, payload: StockMovementRequest):
    try:
        product = inventory_manager.stock_in(product_id, payload.quantity)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_inventory_product(product_id, product)


@app.post("/inventory/{product_id}/stock-out")
def stock_out_endpoint(product_id: str, payload: StockMovementRequest):
    try:
        product = inventory_manager.stock_out(product_id, payload.quantity)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_inventory_product(product_id, product)


@app.get("/inventory")
def list_inventory_endpoint():
    return [
        _serialize_inventory_product(product_id, product)
        for product_id, product in inventory_manager.products.items()
    ]

def _serialize_cart(cart):
    items = []
    for product_id, quantity in cart.items.items():
        product = product_catalog.find_product(product_id)
        if product is None:
            continue
        items.append(
            {
                "product_id": product_id,
                "name": product.name,
                "price": product.price,
                "quantity": quantity,
                "subtotal": product.price * quantity,
            }
        )
    return {
        "cart_id": cart.cart_id,
        "items": items,
        "total": cart_registry.total(cart),
        "is_checked_out": cart.is_checked_out,
    }


@app.post("/products")
def create_product_endpoint(payload: CreateProductRequest):
    try:
        product_id = product_catalog.add_product(
            payload.name, payload.price, payload.stock
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"product_id": product_id}


@app.post("/carts/{cart_id}/items")
def add_cart_item_endpoint(cart_id: str, payload: AddCartItemRequest):
    try:
        cart = cart_registry.add_item(
            cart_id, payload.product_id, payload.quantity
        )
        return _serialize_cart(cart)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/carts/{cart_id}/items/{product_id}")
def remove_cart_item_endpoint(cart_id: str, product_id: str):
    try:
        return _serialize_cart(cart_registry.remove_item(cart_id, product_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/carts/{cart_id}")
def get_cart_endpoint(cart_id: str):
    cart = cart_registry.find_cart(cart_id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    return _serialize_cart(cart)


@app.post("/orders")
def create_order_endpoint(payload: CreateOrderRequest):
    try:
        order_id = order_manager.create_order(payload.cart_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    order = order_manager.find_order(order_id)
    return {"order_id": order_id, "total": order.total}


def _serialize_coupon(coupon: Coupon):
    return {
        "coupon_id": coupon.coupon_id,
        "code": coupon.code,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "min_order_value": coupon.min_order_value,
        "max_discount_amount": coupon.max_discount_amount,
        "max_uses": coupon.max_uses,
        "uses_count": coupon.uses_count,
        "expires_at": (
            coupon.expires_at.isoformat() if coupon.expires_at else None
        ),
        "is_active": coupon.is_active,
        "created_at": coupon.created_at.isoformat(),
    }


@app.post("/coupons", status_code=201)
def create_coupon_endpoint(
    payload: CreateCouponRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        coupon = coupon_service.create_coupon(
            code=payload.code,
            discount_type=payload.discount_type,
            discount_value=payload.discount_value,
            min_order_value=payload.min_order_value,
            max_discount_amount=payload.max_discount_amount,
            max_uses=payload.max_uses,
            expires_at=payload.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_coupon(coupon)


@app.get("/coupons/active")
def list_active_coupons_endpoint():
    coupons = coupon_service.list_active_coupons()
    return [_serialize_coupon(coupon) for coupon in coupons]


@app.post("/coupons/validate")
def validate_coupon_endpoint(payload: ValidateCouponRequest):
    return coupon_service.validate_coupon(
        code=payload.code, order_amount=payload.order_amount
    )


@app.delete("/coupons/{code}", status_code=204)
def delete_coupon_endpoint(
    code: str,
    current_user: User = Depends(get_current_user),
):
    try:
        coupon_service.deactivate_coupon(code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@app.get("/analytics/dashboard")
def get_analytics_dashboard_endpoint():
    return analytics_service.get_dashboard_summary()


@app.get("/analytics/sales-chart")
def get_sales_chart_endpoint(period: str = "day"):
    try:
        return analytics_service.get_sales_chart(period=period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/analytics/low-stock-alert")
def get_low_stock_alert_endpoint(threshold: int = 10):
    try:
        return analytics_service.get_low_stock_alerts(threshold=threshold)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/books")
def add_book_endpoint(payload: AddBookRequest):
    book_id = catalog.add_book(payload.title, payload.author)
    return {"book_id": book_id}


@app.get("/books")
def list_books_endpoint():
    return [
        {
            "book_id": book_id,
            "title": book.title,
            "author": book.author,
            "is_borrowed": book.is_borrowed,
        }
        for book_id, book in catalog.books.items()
    ]


@app.post("/members")
def register_member_endpoint(payload: RegisterMemberRequest):
    member_id = member_registry.register(payload.name, payload.email)
    return {"member_id": member_id}


@app.get("/members/{member_id}")
def get_member_endpoint(member_id: str):
    member = member_registry.find_member(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"name": member.name, "email": member.email}


@app.post("/loans")
def borrow_book_endpoint(payload: BorrowBookRequest):
    try:
        loan_id = loan_manager.borrow_book(payload.book_id, payload.member_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"loan_id": loan_id}


@app.post("/loans/{loan_id}/return")
def return_book_endpoint(loan_id: str):
    try:
        loan_manager.return_book(loan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "returned"}

def _get_account(account_id: str) -> BankAccount:
    account = account_registry.get(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@app.post("/accounts")
def create_account_endpoint(payload: CreateAccountRequest | None = None):
    initial_balance = payload.initial_balance if payload is not None else 0
    try:
        account = BankAccount(initial_balance)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    account_id = uuid4().hex
    account_registry[account_id] = account
    return {"account_id": account_id}


@app.post("/accounts/{account_id}/deposit")
def deposit_endpoint(account_id: str, payload: AccountTransactionRequest):
    account = _get_account(account_id)
    try:
        account.deposit(payload.amount)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"balance": account.get_balance()}


@app.post("/accounts/{account_id}/withdraw")
def withdraw_endpoint(account_id: str, payload: AccountTransactionRequest):
    account = _get_account(account_id)
    try:
        account.withdraw(payload.amount)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"balance": account.get_balance()}


@app.get("/accounts/{account_id}/balance")
def balance_endpoint(account_id: str):
    return {"balance": _get_account(account_id).get_balance()}

@app.get("/")
def read_root():
    return {"status": "OK", "message": "FastAPI service is running"}


@app.get("/add")
def add_endpoint(a: int = 0, b: int = 0):
    return {"result": add(a, b)}


@app.get("/increment")
def increment_endpoint(a: int = 0):
    return {"result": increment(a)}


@app.get("/subtract")
def subtract_endpoint(a: int = 0, b: int = 0):
    return {"result": subtract(a, b)}


@app.get("/multiply")
def multiply_endpoint(a: int = 0, b: int = 0):
    return {"result": multiply(a, b)}


@app.get("/divide")
def divide_endpoint(a: int = 0, b: int = 0):
    return {"result": divide(a, b)}


@app.get("/modulo")
def modulo_endpoint(a: int = 0, b: int = 0):
    return {"result": modulo(a, b)}


@app.get("/average")
def average_endpoint(a: int = 0, b: int = 0):
    return {"result": average(a, b)}


@app.get("/fibonacci")
def fibonacci_endpoint(n: int = 0):
    try:
        return {"result": fibonacci(n)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/stats")
def stats_endpoint(numbers: str = ""):
    try:
        if not numbers.strip():
            raise ValueError("numbers must not be empty")
        parsed_numbers = [float(value.strip()) for value in numbers.split(",")]
        if not all(isfinite(number) for number in parsed_numbers):
            raise ValueError("numbers must contain only finite numeric values")
        return {
            "mean": mean(parsed_numbers),
            "median": median(parsed_numbers),
            "stddev": stddev(parsed_numbers),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/lcm")
def lcm_endpoint(a: int = 0, b: int = 0):
    return {"result": lcm(a, b)}

@app.get("/is-prime")
def is_prime_endpoint(n: int = 0):
    try:
        return {"is_prime": is_prime(n)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/palindrome")
def palindrome_endpoint(text: str):
    return {"is_palindrome": is_palindrome(text)}

@app.get("/convert-temp")
def convert_temp_endpoint(value: float, unit: str):
    if unit == "C":
        return {"result": celsius_to_fahrenheit(value)}
    if unit == "F":
        return {"result": fahrenheit_to_celsius(value)}
    raise HTTPException(status_code=400, detail="unit must be 'C' or 'F'")

@app.get("/sort")
def sort_endpoint(numbers: str = ""):
    try:
        if not numbers.strip():
            raise ValueError("numbers must not be empty")
        parsed_numbers = [float(value.strip()) for value in numbers.split(",")]
        if not all(isfinite(number) for number in parsed_numbers):
            raise ValueError("numbers must contain only finite numeric values")
        return {"result": sort_numbers(parsed_numbers)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/clamp")
def clamp_endpoint(value: float, min_value: float, max_value: float):
    try:
        return {"result": clamp(value, min_value, max_value)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/factorial")
def factorial_endpoint(n: int = 0):
    try:
        return {"result": factorial(n)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/reverse-list")
def reverse_list_endpoint(items: str = ""):
    parsed_items = [] if not items else [item.strip() for item in items.split(",")]
    return {"result": reverse_list(parsed_items)}

@app.get("/word-count")
def word_count_endpoint(text: str = ""):
    return {"result": word_count(text)}

@app.get("/is-leap-year")
def is_leap_year_endpoint(year: int):
    return {"is_leap_year": is_leap_year(year)}

@app.get("/to-binary")
def to_binary_endpoint(n: int = 0):
    try:
        return {"result": to_binary(n)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/count-vowels")
def count_vowels_endpoint(text: str = ""):
    return {"result": count_vowels(text)}

@app.get("/is-anagram")
def is_anagram_endpoint(a: str, b: str):
    return {"is_anagram": is_anagram(a, b)}

@app.get("/compound-interest")
def compound_interest_endpoint(principal: float, rate: float, years: float):
    try:
        return {"result": compound_interest(principal, rate, years)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/bmi")
def bmi_endpoint(weight: float, height: float):
    try:
        bmi_value = calculate_bmi(weight, height)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"bmi": round(bmi_value, 2), "category": classify_bmi(bmi_value)}

@app.get("/greet")
def greet_endpoint(name: str):
    return {"message": greet(name)}


@app.get("/power")
def power_endpoint(a: int = 0, b: int = 0):
    try:
        return {"result": power(a, b)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("src.app:app", host=host, port=port, reload=False)

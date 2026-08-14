from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from src.shop.catalog import ProductCatalog


class Review:
    def __init__(
        self,
        product_id: str,
        user_id: str,
        rating: int,
        comment: str = "",
    ) -> None:
        self.review_id = uuid4().hex
        self.product_id = product_id
        self.user_id = user_id
        self.rating = rating
        self.comment = comment.strip()
        now = datetime.now(timezone.utc)
        self.created_at = now
        self.updated_at = now

    def update(self, rating: int, comment: str = "") -> None:
        self.rating = rating
        self.comment = comment.strip()
        self.updated_at = datetime.now(timezone.utc)


class ReviewService:
    def __init__(
        self,
        product_catalog: ProductCatalog,
        mean_function: Callable[[list[int | float]], float],
    ) -> None:
        self.product_catalog = product_catalog
        self.mean_function = mean_function
        self.reviews: dict[str, Review] = {}
        self.review_ids_by_product_user: dict[tuple[str, str], str] = {}

    def create(
        self,
        product_id: str,
        user_id: str,
        rating: int,
        comment: str = "",
    ) -> Review:
        self._require_product(product_id)
        self._validate_rating(rating)
        key = (product_id, user_id)
        if key in self.review_ids_by_product_user:
            raise ValueError("user has already reviewed this product")

        review = Review(product_id, user_id, rating, comment)
        self.reviews[review.review_id] = review
        self.review_ids_by_product_user[key] = review.review_id
        return review

    def list_for_product(self, product_id: str) -> list[Review]:
        self._require_product(product_id)
        return [
            review
            for review in self.reviews.values()
            if review.product_id == product_id
        ]

    def update_mine(
        self,
        product_id: str,
        user_id: str,
        rating: int,
        comment: str = "",
    ) -> Review:
        self._require_product(product_id)
        self._validate_rating(rating)
        review = self._find_mine(product_id, user_id)
        review.update(rating, comment)
        return review

    def delete_mine(self, product_id: str, user_id: str) -> None:
        self._require_product(product_id)
        review = self._find_mine(product_id, user_id)
        del self.reviews[review.review_id]
        del self.review_ids_by_product_user[(product_id, user_id)]

    def rating_summary(self, product_id: str) -> tuple[float | None, int]:
        reviews = self.list_for_product(product_id)
        if not reviews:
            return None, 0
        ratings = [review.rating for review in reviews]
        return self.mean_function(ratings), len(ratings)

    def _find_mine(self, product_id: str, user_id: str) -> Review:
        review_id = self.review_ids_by_product_user.get((product_id, user_id))
        review = self.reviews.get(review_id) if review_id is not None else None
        if review is None:
            raise KeyError("review not found")
        return review

    def _require_product(self, product_id: str) -> None:
        if self.product_catalog.find_product(product_id) is None:
            raise KeyError("product not found")

    @staticmethod
    def _validate_rating(rating: int) -> None:
        if rating < 1 or rating > 5:
            raise ValueError("rating must be between 1 and 5")

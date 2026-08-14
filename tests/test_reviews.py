import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service, product_catalog, review_service
from src.reviews.service import ReviewService
from src.shop.catalog import ProductCatalog

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    product_catalog.products.clear()
    review_service.reviews.clear()
    review_service.review_ids_by_product_user.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    product_catalog.products.clear()
    review_service.reviews.clear()
    review_service.review_ids_by_product_user.clear()


def auth_headers(name="Alice", email="alice@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def test_review_service_crud_and_uniqueness():
    catalog = ProductCatalog()
    product_id = catalog.add_product("Keyboard", 50, 3)
    service = ReviewService(catalog, lambda ratings: sum(ratings) / len(ratings))

    review = service.create(product_id, "user", 4, " Good ")
    assert review.rating == 4
    assert review.comment == "Good"
    assert service.list_for_product(product_id) == [review]

    with pytest.raises(ValueError, match="user has already reviewed this product"):
        service.create(product_id, "user", 5)

    updated = service.update_mine(product_id, "user", 5, "Excellent")
    assert updated is review
    assert updated.rating == 5
    assert updated.comment == "Excellent"

    service.delete_mine(product_id, "user")
    assert service.list_for_product(product_id) == []


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_review_rating_validation(rating):
    catalog = ProductCatalog()
    product_id = catalog.add_product("Keyboard", 50, 3)
    service = ReviewService(catalog, lambda ratings: 0)
    with pytest.raises(ValueError, match="rating must be between 1 and 5"):
        service.create(product_id, "user", rating)


def test_review_service_rejects_missing_product_or_review():
    catalog = ProductCatalog()
    service = ReviewService(catalog, lambda ratings: 0)
    with pytest.raises(KeyError, match="product not found"):
        service.create("missing", "user", 5)

    product_id = catalog.add_product("Keyboard", 50, 3)
    with pytest.raises(KeyError, match="review not found"):
        service.update_mine(product_id, "user", 5)
    with pytest.raises(KeyError, match="review not found"):
        service.delete_mine(product_id, "user")


def test_rating_summary_reuses_mean_helper():
    calls = []

    def tracked_mean(ratings):
        calls.append(ratings)
        return 4.5

    catalog = ProductCatalog()
    product_id = catalog.add_product("Keyboard", 50, 3)
    service = ReviewService(catalog, tracked_mean)
    service.create(product_id, "first", 4)
    service.create(product_id, "second", 5)

    assert service.rating_summary(product_id) == (4.5, 2)
    assert calls == [[4, 5]]


def test_rating_summary_for_product_without_reviews():
    catalog = ProductCatalog()
    product_id = catalog.add_product("Keyboard", 50, 3)
    service = ReviewService(catalog, lambda ratings: 0)
    assert service.rating_summary(product_id) == (None, 0)


def test_review_endpoint_lifecycle_and_average():
    _, headers = auth_headers()
    product_id = product_catalog.add_product("Keyboard", 50, 3)

    create = client.post(
        f"/products/{product_id}/reviews",
        json={"rating": 4, "comment": "Good"},
        headers=headers,
    )
    assert create.status_code == 201
    created = create.json()
    assert created["rating"] == 4
    assert created["comment"] == "Good"
    assert "user_id" not in created

    listing = client.get(f"/products/{product_id}/reviews")
    assert listing.status_code == 200
    assert listing.json() == [created]

    rating = client.get(f"/products/{product_id}/rating")
    assert rating.json() == {
        "product_id": product_id,
        "average_rating": 4.0,
        "review_count": 1,
    }

    update = client.patch(
        f"/products/{product_id}/reviews/me",
        json={"rating": 5, "comment": "Excellent"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["rating"] == 5

    delete = client.delete(
        f"/products/{product_id}/reviews/me", headers=headers
    )
    assert delete.status_code == 204
    assert client.get(f"/products/{product_id}/reviews").json() == []


def test_multiple_users_contribute_to_average():
    _, first_headers = auth_headers()
    _, second_headers = auth_headers("Bob", "bob@example.com")
    product_id = product_catalog.add_product("Keyboard", 50, 3)

    client.post(
        f"/products/{product_id}/reviews",
        json={"rating": 4},
        headers=first_headers,
    )
    client.post(
        f"/products/{product_id}/reviews",
        json={"rating": 5},
        headers=second_headers,
    )
    assert client.get(f"/products/{product_id}/rating").json() == {
        "product_id": product_id,
        "average_rating": 4.5,
        "review_count": 2,
    }


def test_duplicate_review_returns_400():
    _, headers = auth_headers()
    product_id = product_catalog.add_product("Keyboard", 50, 3)
    path = f"/products/{product_id}/reviews"
    assert client.post(path, json={"rating": 4}, headers=headers).status_code == 201
    response = client.post(path, json={"rating": 5}, headers=headers)
    assert response.status_code == 400
    assert response.json() == {
        "detail": "user has already reviewed this product"
    }


def test_users_cannot_update_or_delete_others_review():
    _, owner_headers = auth_headers()
    _, other_headers = auth_headers("Bob", "bob@example.com")
    product_id = product_catalog.add_product("Keyboard", 50, 3)
    client.post(
        f"/products/{product_id}/reviews",
        json={"rating": 4},
        headers=owner_headers,
    )

    update = client.patch(
        f"/products/{product_id}/reviews/me",
        json={"rating": 1},
        headers=other_headers,
    )
    assert update.status_code == 404
    delete = client.delete(
        f"/products/{product_id}/reviews/me", headers=other_headers
    )
    assert delete.status_code == 404


def test_review_endpoints_handle_missing_product():
    _, headers = auth_headers()
    assert client.post(
        "/products/missing/reviews",
        json={"rating": 5},
        headers=headers,
    ).status_code == 404
    assert client.get("/products/missing/reviews").status_code == 404
    assert client.get("/products/missing/rating").status_code == 404


def test_review_mutations_require_authentication():
    product_id = product_catalog.add_product("Keyboard", 50, 3)
    assert client.post(
        f"/products/{product_id}/reviews", json={"rating": 5}
    ).status_code == 401
    assert client.patch(
        f"/products/{product_id}/reviews/me", json={"rating": 5}
    ).status_code == 401
    assert client.delete(
        f"/products/{product_id}/reviews/me"
    ).status_code == 401

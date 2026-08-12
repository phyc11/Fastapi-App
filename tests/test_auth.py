import jwt
import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service
from src.auth.service import AuthService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_users():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()


def test_register_hashes_password_and_normalizes_email():
    service = AuthService(secret="test-secret")
    user = service.register(" Alice ", " Alice@Example.COM ", "password123")

    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.password_hash != "password123"
    assert "password123" not in user.password_hash
    assert service.password_hash.verify("password123", user.password_hash)


@pytest.mark.parametrize(
    ("name", "email", "password", "message"),
    [
        ("", "alice@example.com", "password123", "name must not be empty"),
        ("Alice", "invalid", "password123", "email must be valid"),
        (
            "Alice",
            "alice@example.com",
            "short",
            "password must be at least 8 characters",
        ),
    ],
)
def test_register_validates_user(name, email, password, message):
    service = AuthService(secret="test-secret")
    with pytest.raises(ValueError, match=message):
        service.register(name, email, password)


def test_register_rejects_duplicate_email_case_insensitively():
    service = AuthService(secret="test-secret")
    service.register("Alice", "alice@example.com", "password123")
    with pytest.raises(ValueError, match="email is already registered"):
        service.register("Other", "ALICE@example.com", "password456")


def test_authenticate_accepts_valid_credentials():
    service = AuthService(secret="test-secret")
    registered = service.register(
        "Alice", "alice@example.com", "password123"
    )
    authenticated = service.authenticate(
        "ALICE@example.com", "password123"
    )
    assert authenticated is registered


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("missing@example.com", "password123"),
        ("alice@example.com", "wrong-password"),
    ],
)
def test_authenticate_rejects_invalid_credentials(email, password):
    service = AuthService(secret="test-secret")
    service.register("Alice", "alice@example.com", "password123")
    with pytest.raises(ValueError, match="invalid email or password"):
        service.authenticate(email, password)


def test_access_token_round_trip():
    service = AuthService(secret="test-secret")
    user = service.register("Alice", "alice@example.com", "password123")
    token = service.create_access_token(user)

    payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
    assert payload["sub"] == user.user_id
    assert "iat" in payload
    assert "exp" in payload
    assert service.get_user_from_token(token) is user


def test_expired_or_tampered_token_is_rejected():
    service = AuthService(secret="test-secret", access_token_minutes=-1)
    user = service.register("Alice", "alice@example.com", "password123")
    with pytest.raises(ValueError, match="invalid or expired access token"):
        service.get_user_from_token(service.create_access_token(user))

    other_service = AuthService(secret="other-secret")
    valid_service = AuthService(secret="test-secret")
    other_user = other_service.register(
        "Alice", "alice@example.com", "password123"
    )
    with pytest.raises(ValueError, match="invalid or expired access token"):
        valid_service.get_user_from_token(
            other_service.create_access_token(other_user)
        )


def test_auth_endpoint_lifecycle():
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Alice",
            "email": "Alice@example.com",
            "password": "password123",
        },
    )
    assert register_response.status_code == 201
    user = register_response.json()
    assert user["name"] == "Alice"
    assert user["email"] == "alice@example.com"
    assert "password" not in user
    stored_user = auth_service.users[user["user_id"]]
    assert stored_user.password_hash != "password123"

    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["token_type"] == "bearer"

    me_response = client.get(
        "/users/me",
        headers={
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        },
    )
    assert me_response.status_code == 200
    assert me_response.json() == user


def test_register_endpoint_rejects_duplicate_email():
    payload = {
        "name": "Alice",
        "email": "alice@example.com",
        "password": "password123",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": "email is already registered"}


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("missing@example.com", "password123"),
        ("alice@example.com", "wrong-password"),
    ],
)
def test_login_endpoint_rejects_invalid_credentials(email, password):
    auth_service.register("Alice", "alice@example.com", "password123")
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid email or password"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer invalid-token"},
        {"Authorization": "Basic credentials"},
    ],
)
def test_users_me_requires_valid_bearer_token(headers):
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_users_me_rejects_token_when_user_no_longer_exists():
    user = auth_service.register(
        "Alice", "alice@example.com", "password123"
    )
    token = auth_service.create_access_token(user)
    auth_service.users.clear()

    response = client.get(
        "/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid or expired access token"}

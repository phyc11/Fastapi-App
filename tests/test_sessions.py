import hashlib

import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service
from src.auth.service import AuthService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_auth_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()


def register_and_login():
    client.post(
        "/auth/register",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "password123",
        },
    )
    return client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    ).json()


def test_create_session_hashes_refresh_token():
    service = AuthService(secret="a-secure-test-secret-that-is-32-bytes")
    user = service.register("Alice", "alice@example.com", "password123")

    access_token, refresh_token = service.create_session(user)
    session = next(iter(service.sessions.values()))

    assert refresh_token not in session.refresh_token_hash
    assert session.refresh_token_hash == hashlib.sha256(
        refresh_token.encode()
    ).hexdigest()
    assert service.get_user_from_token(access_token) is user


def test_refresh_rotates_token_and_rejects_reuse():
    service = AuthService(secret="a-secure-test-secret-that-is-32-bytes")
    user = service.register("Alice", "alice@example.com", "password123")
    _, first_refresh = service.create_session(user)

    access_token, second_refresh = service.refresh(first_refresh)
    assert second_refresh != first_refresh
    assert service.get_user_from_token(access_token) is user
    with pytest.raises(ValueError, match="invalid or expired refresh token"):
        service.refresh(first_refresh)


def test_revoke_invalidates_access_and_refresh_tokens():
    service = AuthService(secret="a-secure-test-secret-that-is-32-bytes")
    user = service.register("Alice", "alice@example.com", "password123")
    access_token, refresh_token = service.create_session(user)

    session = service.revoke_access_token(access_token)
    assert session.is_active is False
    with pytest.raises(ValueError, match="invalid or expired access token"):
        service.get_user_from_token(access_token)
    with pytest.raises(ValueError, match="invalid or expired refresh token"):
        service.refresh(refresh_token)


def test_expired_refresh_token_is_rejected():
    service = AuthService(
        secret="a-secure-test-secret-that-is-32-bytes",
        refresh_token_days=-1,
    )
    user = service.register("Alice", "alice@example.com", "password123")
    _, refresh_token = service.create_session(user)
    with pytest.raises(ValueError, match="invalid or expired refresh token"):
        service.refresh(refresh_token)


def test_list_sessions_only_returns_users_sessions():
    service = AuthService(secret="a-secure-test-secret-that-is-32-bytes")
    first = service.register("Alice", "alice@example.com", "password123")
    second = service.register("Bob", "bob@example.com", "password123")
    service.create_session(first)
    service.create_session(first)
    service.create_session(second)

    assert len(service.list_sessions(first.user_id)) == 2
    assert len(service.list_sessions(second.user_id)) == 1


def test_refresh_and_logout_endpoint_lifecycle():
    tokens = register_and_login()
    original_refresh = tokens["refresh_token"]

    refresh_response = client.post(
        "/auth/refresh", json={"refresh_token": original_refresh}
    )
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert refreshed["refresh_token"] != original_refresh
    assert refreshed["token_type"] == "bearer"
    assert refreshed["expires_in"] == 900

    reuse_response = client.post(
        "/auth/refresh", json={"refresh_token": original_refresh}
    )
    assert reuse_response.status_code == 401

    logout_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    )
    assert logout_response.status_code == 204

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {refreshed['access_token']}"},
    )
    assert me_response.status_code == 401
    refresh_after_logout = client.post(
        "/auth/refresh", json={"refresh_token": refreshed["refresh_token"]}
    )
    assert refresh_after_logout.status_code == 401


def test_sessions_endpoint_returns_metadata_without_secrets():
    first = register_and_login()
    second = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    ).json()

    client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )
    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    )
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 2
    assert [session["is_active"] for session in sessions] == [False, True]
    assert sessions[0]["revoked_at"] is not None
    assert sessions[1]["revoked_at"] is None
    assert all("refresh_token" not in session for session in sessions)
    assert all("refresh_token_hash" not in session for session in sessions)


def test_auth_session_endpoints_require_valid_credentials():
    assert client.post("/auth/logout").status_code == 401
    assert client.get("/auth/sessions").status_code == 401
    response = client.post(
        "/auth/refresh", json={"refresh_token": "invalid"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid or expired refresh token"}

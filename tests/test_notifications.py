import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service, notification_service
from src.notifications.service import NotificationService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    notification_service.notifications.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    notification_service.notifications.clear()


def auth_headers(name="Alice", email="alice@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("notification_type", ["email", "sms", "in_app"])
def test_create_notification_for_supported_types(notification_type):
    service = NotificationService()
    notification = service.create("user-1", notification_type, " Hello ")

    assert notification.user_id == "user-1"
    assert notification.notification_type == notification_type
    assert notification.message == "Hello"
    assert notification.status == "pending"
    assert service.notifications[notification.notification_id] is notification


@pytest.mark.parametrize(
    ("notification_type", "message", "error"),
    [
        ("push", "Hello", "type must be 'email', 'sms', or 'in_app'"),
        ("email", "   ", "message must not be empty"),
    ],
)
def test_create_notification_validates_input(
    notification_type, message, error
):
    service = NotificationService()
    with pytest.raises(ValueError, match=error):
        service.create("user-1", notification_type, message)


def test_list_for_user_isolates_notifications():
    service = NotificationService()
    first = service.create("user-1", "email", "First")
    service.create("user-2", "sms", "Other")
    second = service.create("user-1", "in_app", "Second")

    assert service.list_for_user("user-1") == [first, second]


def test_notification_supports_sent_failed_and_read_statuses():
    service = NotificationService()
    sent = service.create("user-1", "email", "Sent")
    failed = service.create("user-1", "sms", "Failed")
    read = service.create("user-1", "in_app", "Read")

    service.mark_sent(sent.notification_id)
    service.mark_failed(failed.notification_id)
    service.mark_read(read.notification_id, "user-1")

    assert sent.status == "sent"
    assert failed.status == "failed"
    assert read.status == "read"
    assert all(
        notification.updated_at >= notification.created_at
        for notification in (sent, failed, read)
    )


def test_mark_read_rejects_missing_or_other_users_notification():
    service = NotificationService()
    notification = service.create("user-1", "in_app", "Hello")

    with pytest.raises(KeyError, match="notification not found"):
        service.mark_read("missing", "user-1")
    with pytest.raises(KeyError, match="notification not found"):
        service.mark_read(notification.notification_id, "user-2")
    assert notification.status == "pending"


def test_notification_endpoint_lifecycle():
    _, headers = auth_headers()

    create_response = client.post(
        "/notifications",
        json={"type": "in_app", "message": "Order shipped"},
        headers=headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["type"] == "in_app"
    assert created["message"] == "Order shipped"
    assert created["status"] == "pending"
    assert created["created_at"]
    assert created["updated_at"]

    list_response = client.get("/notifications/me", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json() == [created]

    read_response = client.patch(
        f"/notifications/{created['notification_id']}/read",
        headers=headers,
    )
    assert read_response.status_code == 200
    assert read_response.json()["status"] == "read"


def test_notification_endpoints_require_authentication():
    assert client.post(
        "/notifications", json={"type": "email", "message": "Hello"}
    ).status_code == 401
    assert client.get("/notifications/me").status_code == 401
    assert client.patch("/notifications/id/read").status_code == 401


def test_notification_endpoint_returns_400_for_invalid_input():
    _, headers = auth_headers()
    response = client.post(
        "/notifications",
        json={"type": "push", "message": "Hello"},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "type must be 'email', 'sms', or 'in_app'"
    }


def test_users_only_see_and_update_their_notifications():
    first_user, first_headers = auth_headers()
    _, second_headers = auth_headers("Bob", "bob@example.com")
    notification = notification_service.create(
        first_user.user_id, "in_app", "Private"
    )

    assert client.get(
        "/notifications/me", headers=second_headers
    ).json() == []
    response = client.patch(
        f"/notifications/{notification.notification_id}/read",
        headers=second_headers,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "notification not found"}
    assert notification.status == "pending"


def test_notification_endpoints_delegate_to_service(monkeypatch):
    user, headers = auth_headers()
    calls = []
    original_create = notification_service.create
    original_list = notification_service.list_for_user
    original_mark_read = notification_service.mark_read

    def tracked_create(user_id, notification_type, message):
        calls.append(("create", user_id, notification_type, message))
        return original_create(user_id, notification_type, message)

    def tracked_list(user_id):
        calls.append(("list", user_id))
        return original_list(user_id)

    def tracked_mark_read(notification_id, user_id):
        calls.append(("read", notification_id, user_id))
        return original_mark_read(notification_id, user_id)

    monkeypatch.setattr(notification_service, "create", tracked_create)
    monkeypatch.setattr(notification_service, "list_for_user", tracked_list)
    monkeypatch.setattr(notification_service, "mark_read", tracked_mark_read)

    created = client.post(
        "/notifications",
        json={"type": "email", "message": "Hello"},
        headers=headers,
    ).json()
    client.get("/notifications/me", headers=headers)
    client.patch(
        f"/notifications/{created['notification_id']}/read", headers=headers
    )

    assert calls == [
        ("create", user.user_id, "email", "Hello"),
        ("list", user.user_id),
        ("read", created["notification_id"], user.user_id),
    ]

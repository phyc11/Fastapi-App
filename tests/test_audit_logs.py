from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src.app import app, audit_log_service, auth_service
from src.audit_logs.service import AuditLogService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    audit_log_service.logs.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    audit_log_service.logs.clear()


def auth_headers(name="Audit User", email="audit@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def test_audit_log_service_filtering_and_sorting():
    service = AuditLogService()
    now = datetime.now(timezone.utc)

    service.record_log("u1", "LOGIN", "/auth/login", "192.168.1.10", "Mozilla/5.0", timestamp=now - timedelta(hours=2))
    service.record_log("u1", "UPDATE_PROFILE", "/users/me", "192.168.1.10", "Mozilla/5.0", timestamp=now - timedelta(hours=1))
    service.record_log("u2", "LOGIN", "/auth/login", "10.0.0.1", "Chrome/100", timestamp=now)

    # Test get_user_logs
    u1_logs = service.get_user_logs("u1")
    assert len(u1_logs) == 2
    assert u1_logs[0].action == "UPDATE_PROFILE"  # latest first
    assert u1_logs[1].action == "LOGIN"

    # Test search_logs by action
    login_logs = service.search_logs(action="login")
    assert len(login_logs) == 2

    # Test search_logs by IP
    ip_logs = service.search_logs(ip_address="10.0.0.1")
    assert len(ip_logs) == 1
    assert ip_logs[0].user_id == "u2"

    # Test search_logs by date range
    recent_logs = service.search_logs(start_date=now - timedelta(minutes=30))
    assert len(recent_logs) == 1
    assert recent_logs[0].user_id == "u2"

    # Error handling
    with pytest.raises(ValueError, match="action must not be empty"):
        service.record_log("u1", "  ")


def test_audit_logs_endpoints_and_auto_logging():
    # 1. Register user (POST /auth/register) -> triggers USER_REGISTER audit log
    reg_res = client.post(
        "/auth/register",
        json={"name": "Audit Tester", "email": "tester@example.com", "password": "password123"},
    )
    assert reg_res.status_code == 201

    # 2. Login user (POST /auth/login) -> triggers USER_LOGIN audit log
    login_res = client.post(
        "/auth/login",
        json={"email": "tester@example.com", "password": "password123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. GET /audit-logs/me
    my_logs_res = client.get("/audit-logs/me", headers=headers)
    assert my_logs_res.status_code == 200
    logs = my_logs_res.json()
    assert len(logs) == 2
    actions = {item["action"] for item in logs}
    assert "USER_REGISTER" in actions
    assert "USER_LOGIN" in actions

    # 4. GET /audit-logs/admin with filter
    admin_logs_res = client.get("/audit-logs/admin?action=USER_LOGIN", headers=headers)
    assert admin_logs_res.status_code == 200
    admin_logs = admin_logs_res.json()
    assert len(admin_logs) == 1
    assert admin_logs[0]["action"] == "USER_LOGIN"


def test_audit_logs_unauthenticated():
    assert client.get("/audit-logs/me").status_code == 401
    assert client.get("/audit-logs/admin").status_code == 401

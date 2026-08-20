import pytest
from fastapi.testclient import TestClient

from src.app import app, auth_service, ticket_service
from src.tickets.service import TicketService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_state():
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    ticket_service.tickets.clear()
    yield
    auth_service.users.clear()
    auth_service.user_ids_by_email.clear()
    auth_service.sessions.clear()
    ticket_service.tickets.clear()


def auth_headers(name="Customer User", email="customer@example.com"):
    user = auth_service.register(name, email, "password123")
    token = auth_service.create_access_token(user)
    return user, {"Authorization": f"Bearer {token}"}


def test_ticket_service_creation_and_reply_flow():
    service = TicketService()
    ticket = service.create_ticket(
        user_id="user-1",
        title="Damaged Package",
        category="shipping",
        description="The package arrived damaged.",
        attachments=["http://example.com/photo.jpg"],
    )

    assert ticket.user_id == "user-1"
    assert ticket.title == "Damaged Package"
    assert ticket.category == "shipping"
    assert ticket.description == "The package arrived damaged."
    assert ticket.status == "open"
    assert len(ticket.attachments) == 1

    # Add reply
    reply = service.add_reply(ticket.ticket_id, "user-1", "Here is another photo", ["http://example.com/photo2.jpg"])
    assert reply.ticket_id == ticket.ticket_id
    assert reply.message == "Here is another photo"
    assert len(ticket.replies) == 1

    # Update status
    updated = service.update_status(ticket.ticket_id, "resolved")
    assert updated.status == "resolved"


def test_ticket_service_input_validations():
    service = TicketService()

    with pytest.raises(ValueError, match="title must not be empty"):
        service.create_ticket("u1", "", "general", "desc")

    with pytest.raises(ValueError, match="category must be one of"):
        service.create_ticket("u1", "Title", "invalid_cat", "desc")

    with pytest.raises(ValueError, match="description must not be empty"):
        service.create_ticket("u1", "Title", "general", "  ")

    ticket = service.create_ticket("u1", "Title", "general", "desc")
    with pytest.raises(ValueError, match="message must not be empty"):
        service.add_reply(ticket.ticket_id, "u1", "   ")

    with pytest.raises(ValueError, match="status must be one of"):
        service.update_status(ticket.ticket_id, "invalid_status")

    with pytest.raises(KeyError, match="ticket not found"):
        service.add_reply("missing_id", "u1", "msg")

    with pytest.raises(KeyError, match="ticket not found"):
        service.update_status("missing_id", "resolved")


def test_ticket_endpoints_full_lifecycle():
    user, headers = auth_headers()

    # 1. Create Ticket (POST /tickets)
    create_res = client.post(
        "/tickets",
        json={
            "title": "Payment Double Charged",
            "category": "payment",
            "description": "I was charged twice for order #1234",
            "attachments": ["http://example.com/receipt.pdf"],
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["title"] == "Payment Double Charged"
    assert created["category"] == "payment"
    assert created["status"] == "open"
    ticket_id = created["ticket_id"]

    # 2. List User Tickets (GET /tickets/me)
    list_res = client.get("/tickets/me", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["ticket_id"] == ticket_id

    # 3. Get Ticket Detail (GET /tickets/{ticket_id})
    detail_res = client.get(f"/tickets/{ticket_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["ticket_id"] == ticket_id

    # 4. Add Reply (POST /tickets/{ticket_id}/replies)
    reply_res = client.post(
        f"/tickets/{ticket_id}/replies",
        json={"message": "Attached additional proof", "attachments": []},
        headers=headers,
    )
    assert reply_res.status_code == 201
    reply_data = reply_res.json()
    assert reply_data["message"] == "Attached additional proof"

    # Verify reply is in ticket detail
    detail_res2 = client.get(f"/tickets/{ticket_id}", headers=headers)
    assert len(detail_res2.json()["replies"]) == 1

    # 5. Update Status (PATCH /tickets/{ticket_id}/status)
    status_res = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "closed"},
        headers=headers,
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "closed"


def test_ticket_endpoints_authorization_and_authentication():
    user1, headers1 = auth_headers("User One", "user1@example.com")
    user2, headers2 = auth_headers("User Two", "user2@example.com")

    # Unauthenticated requests return 401
    assert client.post("/tickets", json={"title": "t", "description": "d"}).status_code == 401
    assert client.get("/tickets/me").status_code == 401
    assert client.get("/tickets/t1").status_code == 401

    # User 1 creates ticket
    create_res = client.post(
        "/tickets",
        json={"title": "User 1 Ticket", "description": "Need help"},
        headers=headers1,
    )
    ticket_id = create_res.json()["ticket_id"]

    # User 2 cannot view or reply or update User 1's ticket (403 Forbidden)
    assert client.get(f"/tickets/{ticket_id}", headers=headers2).status_code == 403
    assert client.post(
        f"/tickets/{ticket_id}/replies",
        json={"message": "hacked"},
        headers=headers2,
    ).status_code == 403
    assert client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "closed"},
        headers=headers2,
    ).status_code == 403

from datetime import datetime, timezone
from uuid import uuid4

VALID_TICKET_CATEGORIES = {
    "order_issue",
    "payment",
    "product_quality",
    "shipping",
    "general",
}
VALID_TICKET_STATUSES = {"open", "pending", "resolved", "closed"}


class TicketReply:
    def __init__(
        self,
        ticket_id: str,
        user_id: str,
        message: str,
        attachments: list[str] | None = None,
    ) -> None:
        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("message must not be empty")

        now = datetime.now(timezone.utc)
        self.reply_id = uuid4().hex
        self.ticket_id = ticket_id
        self.user_id = user_id
        self.message = normalized_message
        self.attachments = attachments or []
        self.created_at = now


class Ticket:
    def __init__(
        self,
        user_id: str,
        title: str,
        category: str,
        description: str,
        attachments: list[str] | None = None,
    ) -> None:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("title must not be empty")

        category_key = category.strip().lower()
        if category_key not in VALID_TICKET_CATEGORIES:
            raise ValueError(
                f"category must be one of {sorted(VALID_TICKET_CATEGORIES)}"
            )

        normalized_desc = description.strip()
        if not normalized_desc:
            raise ValueError("description must not be empty")

        now = datetime.now(timezone.utc)
        self.ticket_id = uuid4().hex
        self.user_id = user_id
        self.title = normalized_title
        self.category = category_key
        self.description = normalized_desc
        self.attachments = attachments or []
        self.status = "open"
        self.replies: list[TicketReply] = []
        self.created_at = now
        self.updated_at = now

    def add_reply(
        self,
        user_id: str,
        message: str,
        attachments: list[str] | None = None,
    ) -> TicketReply:
        reply = TicketReply(
            ticket_id=self.ticket_id,
            user_id=user_id,
            message=message,
            attachments=attachments,
        )
        self.replies.append(reply)
        self.updated_at = datetime.now(timezone.utc)
        return reply

    def set_status(self, status: str) -> None:
        status_key = status.strip().lower()
        if status_key not in VALID_TICKET_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(VALID_TICKET_STATUSES)}"
            )
        self.status = status_key
        self.updated_at = datetime.now(timezone.utc)


class TicketService:
    def __init__(self) -> None:
        self.tickets: dict[str, Ticket] = {}

    def create_ticket(
        self,
        user_id: str,
        title: str,
        category: str,
        description: str,
        attachments: list[str] | None = None,
    ) -> Ticket:
        ticket = Ticket(
            user_id=user_id,
            title=title,
            category=category,
            description=description,
            attachments=attachments,
        )
        self.tickets[ticket.ticket_id] = ticket
        return ticket

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        return self.tickets.get(ticket_id)

    def list_for_user(self, user_id: str) -> list[Ticket]:
        user_tickets = [
            t for t in self.tickets.values() if t.user_id == user_id
        ]
        return sorted(user_tickets, key=lambda t: t.created_at, reverse=True)

    def add_reply(
        self,
        ticket_id: str,
        user_id: str,
        message: str,
        attachments: list[str] | None = None,
    ) -> TicketReply:
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            raise KeyError("ticket not found")
        return ticket.add_reply(user_id=user_id, message=message, attachments=attachments)

    def update_status(self, ticket_id: str, status: str) -> Ticket:
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            raise KeyError("ticket not found")
        ticket.set_status(status)
        return ticket

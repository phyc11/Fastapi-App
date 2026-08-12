from datetime import datetime, timezone
from uuid import uuid4


NOTIFICATION_TYPES = {"email", "sms", "in_app"}
NOTIFICATION_STATUSES = {"pending", "sent", "failed", "read"}


class Notification:
    def __init__(
        self, user_id: str, notification_type: str, message: str
    ) -> None:
        if notification_type not in NOTIFICATION_TYPES:
            raise ValueError("type must be 'email', 'sms', or 'in_app'")
        if not message.strip():
            raise ValueError("message must not be empty")

        now = datetime.now(timezone.utc)
        self.notification_id = uuid4().hex
        self.user_id = user_id
        self.notification_type = notification_type
        self.message = message.strip()
        self.status = "pending"
        self.created_at = now
        self.updated_at = now

    def set_status(self, status: str) -> None:
        if status not in NOTIFICATION_STATUSES:
            raise ValueError("invalid notification status")
        self.status = status
        self.updated_at = datetime.now(timezone.utc)


class NotificationService:
    def __init__(self) -> None:
        self.notifications: dict[str, Notification] = {}

    def create(
        self, user_id: str, notification_type: str, message: str
    ) -> Notification:
        notification = Notification(user_id, notification_type, message)
        self.notifications[notification.notification_id] = notification
        return notification

    def list_for_user(self, user_id: str) -> list[Notification]:
        return [
            notification
            for notification in self.notifications.values()
            if notification.user_id == user_id
        ]

    def find_for_user(
        self, notification_id: str, user_id: str
    ) -> Notification | None:
        notification = self.notifications.get(notification_id)
        if notification is None or notification.user_id != user_id:
            return None
        return notification

    def mark_read(self, notification_id: str, user_id: str) -> Notification:
        notification = self.find_for_user(notification_id, user_id)
        if notification is None:
            raise KeyError("notification not found")
        notification.set_status("read")
        return notification

    def mark_sent(self, notification_id: str) -> Notification:
        return self._set_delivery_status(notification_id, "sent")

    def mark_failed(self, notification_id: str) -> Notification:
        return self._set_delivery_status(notification_id, "failed")

    def _set_delivery_status(
        self, notification_id: str, status: str
    ) -> Notification:
        notification = self.notifications.get(notification_id)
        if notification is None:
            raise KeyError("notification not found")
        notification.set_status(status)
        return notification

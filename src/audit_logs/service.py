from datetime import datetime, timezone
from uuid import uuid4


class AuditLogEntry:
    def __init__(
        self,
        user_id: str | None,
        action: str,
        resource: str = "",
        ip_address: str = "127.0.0.1",
        user_agent: str = "",
        details: dict | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        normalized_action = action.strip().upper()
        if not normalized_action:
            raise ValueError("action must not be empty")

        now = timestamp or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        self.log_id = uuid4().hex
        self.user_id = user_id
        self.action = normalized_action
        self.resource = resource.strip()
        self.ip_address = ip_address.strip() or "127.0.0.1"
        self.user_agent = user_agent.strip()
        self.details = details or {}
        self.timestamp = now


class AuditLogService:
    def __init__(self) -> None:
        self.logs: list[AuditLogEntry] = []

    def record_log(
        self,
        user_id: str | None,
        action: str,
        resource: str = "",
        ip_address: str = "127.0.0.1",
        user_agent: str = "",
        details: dict | None = None,
        timestamp: datetime | None = None,
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            user_id=user_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            timestamp=timestamp,
        )
        self.logs.append(entry)
        return entry

    def get_user_logs(self, user_id: str) -> list[AuditLogEntry]:
        user_entries = [entry for entry in self.logs if entry.user_id == user_id]
        return sorted(user_entries, key=lambda x: x.timestamp, reverse=True)

    def search_logs(
        self,
        action: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[AuditLogEntry]:
        filtered = []

        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        for entry in self.logs:
            if action and action.strip().upper() not in entry.action:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if ip_address and entry.ip_address != ip_address.strip():
                continue
            if start_date and entry.timestamp < start_date:
                continue
            if end_date and entry.timestamp > end_date:
                continue
            filtered.append(entry)

        return sorted(filtered, key=lambda x: x.timestamp, reverse=True)

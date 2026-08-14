import hashlib
import os
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import uuid4

import jwt
from pwdlib import PasswordHash


class User:
    def __init__(
        self, user_id: str, name: str, email: str, password_hash: str
    ) -> None:
        self.user_id = user_id
        self.name = name
        self.email = email
        self.password_hash = password_hash


class Session:
    def __init__(
        self,
        session_id: str,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.session_id = session_id
        self.user_id = user_id
        self.refresh_token_hash = refresh_token_hash
        self.created_at = now
        self.last_used_at = now
        self.expires_at = expires_at
        self.revoked_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return (
            self.revoked_at is None
            and self.expires_at > datetime.now(timezone.utc)
        )


class AuthService:
    def __init__(
        self,
        secret: str | None = None,
        access_token_minutes: int = 15,
        refresh_token_days: int = 7,
    ) -> None:
        self.users: dict[str, User] = {}
        self.user_ids_by_email: dict[str, str] = {}
        self.sessions: dict[str, Session] = {}
        self.password_hash = PasswordHash.recommended()
        self.secret = secret or os.environ.get("JWT_SECRET") or token_urlsafe(32)
        self.access_token_minutes = access_token_minutes
        self.refresh_token_days = refresh_token_days
        self.algorithm = "HS256"

    def register(self, name: str, email: str, password: str) -> User:
        normalized_name = name.strip()
        normalized_email = email.strip().lower()
        if not normalized_name:
            raise ValueError("name must not be empty")
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("email must be valid")
        if len(password) < 8:
            raise ValueError("password must be at least 8 characters")
        if normalized_email in self.user_ids_by_email:
            raise ValueError("email is already registered")

        user_id = uuid4().hex
        user = User(
            user_id,
            normalized_name,
            normalized_email,
            self.password_hash.hash(password),
        )
        self.users[user_id] = user
        self.user_ids_by_email[normalized_email] = user_id
        return user

    def authenticate(self, email: str, password: str) -> User:
        user_id = self.user_ids_by_email.get(email.strip().lower())
        user = self.users.get(user_id) if user_id is not None else None
        if user is None or not self.password_hash.verify(
            password, user.password_hash
        ):
            raise ValueError("invalid email or password")
        return user

    def create_session(self, user: User) -> tuple[str, str]:
        session, refresh_token = self._new_session(user.user_id)
        return self.create_access_token(user, session), refresh_token

    def create_access_token(
        self, user: User, session: Session | None = None
    ) -> str:
        if session is None:
            session, _ = self._new_session(user.user_id)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.user_id,
            "sid": session.session_id,
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_minutes),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        token_hash = self._hash_refresh_token(refresh_token)
        session = next(
            (
                candidate
                for candidate in self.sessions.values()
                if candidate.refresh_token_hash == token_hash
            ),
            None,
        )
        if session is None or not session.is_active:
            raise ValueError("invalid or expired refresh token")

        user = self.users.get(session.user_id)
        if user is None:
            raise ValueError("invalid or expired refresh token")

        new_refresh_token = token_urlsafe(48)
        session.refresh_token_hash = self._hash_refresh_token(new_refresh_token)
        session.last_used_at = datetime.now(timezone.utc)
        return self.create_access_token(user, session), new_refresh_token

    def get_user_from_token(self, token: str) -> User:
        user, _ = self.get_auth_context(token)
        return user

    def get_auth_context(self, token: str) -> tuple[User, Session]:
        try:
            payload = jwt.decode(
                token, self.secret, algorithms=[self.algorithm]
            )
        except jwt.InvalidTokenError as exc:
            raise ValueError("invalid or expired access token") from exc

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        user = self.users.get(user_id) if isinstance(user_id, str) else None
        session = (
            self.sessions.get(session_id)
            if isinstance(session_id, str)
            else None
        )
        if (
            user is None
            or session is None
            or session.user_id != user.user_id
            or not session.is_active
        ):
            raise ValueError("invalid or expired access token")
        return user, session

    def revoke_access_token(self, token: str) -> Session:
        _, session = self.get_auth_context(token)
        session.revoked_at = datetime.now(timezone.utc)
        return session

    def list_sessions(self, user_id: str) -> list[Session]:
        return [
            session
            for session in self.sessions.values()
            if session.user_id == user_id
        ]

    def _new_session(self, user_id: str) -> tuple[Session, str]:
        refresh_token = token_urlsafe(48)
        session_id = uuid4().hex
        session = Session(
            session_id,
            user_id,
            self._hash_refresh_token(refresh_token),
            datetime.now(timezone.utc)
            + timedelta(days=self.refresh_token_days),
        )
        self.sessions[session_id] = session
        return session, refresh_token

    @staticmethod
    def _hash_refresh_token(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()

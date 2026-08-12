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


class AuthService:
    def __init__(
        self,
        secret: str | None = None,
        access_token_minutes: int = 30,
    ) -> None:
        self.users: dict[str, User] = {}
        self.user_ids_by_email: dict[str, str] = {}
        self.password_hash = PasswordHash.recommended()
        self.secret = secret or os.environ.get("JWT_SECRET") or token_urlsafe(32)
        self.access_token_minutes = access_token_minutes
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

    def create_access_token(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.user_id,
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_minutes),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def get_user_from_token(self, token: str) -> User:
        try:
            payload = jwt.decode(
                token, self.secret, algorithms=[self.algorithm]
            )
        except jwt.InvalidTokenError as exc:
            raise ValueError("invalid or expired access token") from exc

        user_id = payload.get("sub")
        user = self.users.get(user_id) if isinstance(user_id, str) else None
        if user is None:
            raise ValueError("invalid or expired access token")
        return user

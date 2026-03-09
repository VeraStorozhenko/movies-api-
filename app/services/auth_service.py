import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Header, HTTPException, status
from sqlmodel import select

from app.config import get_settings
from app.db import get_session
from app.models import AuthToken, RefreshToken, User

PBKDF2_ITERATIONS = 120_000


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    pwd_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        pwd_salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"{pwd_salt}${digest}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected_digest = password_hash.split("$", 1)
    except ValueError:
        return False

    candidate = _hash_password(password, salt=salt).split("$", 1)[1]
    return hmac.compare_digest(candidate, expected_digest)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        return expires_at <= datetime.utcnow()
    return expires_at <= _now()


def _issue_access_token(user_id: int) -> AuthToken:
    settings = get_settings()
    return AuthToken(
        user_id=user_id,
        token=secrets.token_urlsafe(32),
        expires_at=_now() + timedelta(minutes=settings.access_token_ttl_minutes),
    )


def _issue_refresh_token(user_id: int) -> RefreshToken:
    settings = get_settings()
    return RefreshToken(
        user_id=user_id,
        token=secrets.token_urlsafe(48),
        expires_at=_now() + timedelta(days=settings.refresh_token_ttl_days),
    )


def register_user(username: str, password: str) -> User:
    normalized = _normalize_username(username)
    with get_session() as session:
        existing = session.exec(select(User).where(User.username == normalized)).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

        user = User(username=normalized, password_hash=_hash_password(password))
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def login_user(username: str, password: str) -> tuple[AuthToken, RefreshToken, str]:
    normalized = _normalize_username(username)
    with get_session() as session:
        user = session.exec(select(User).where(User.username == normalized)).first()
        if not user or not _verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if user.id is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid user id")

        access = _issue_access_token(user.id)
        refresh = _issue_refresh_token(user.id)
        session.add(access)
        session.add(refresh)
        session.commit()
        session.refresh(access)
        session.refresh(refresh)
        return access, refresh, user.username


def refresh_access_token(refresh_token: str) -> tuple[AuthToken, str]:
    with get_session() as session:
        token_row = session.exec(select(RefreshToken).where(RefreshToken.token == refresh_token)).first()
        if not token_row or token_row.revoked_at is not None or _is_expired(token_row.expires_at):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = session.exec(select(User).where(User.id == token_row.user_id)).first()
        if not user or user.id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        access = _issue_access_token(user.id)
        session.add(access)
        session.commit()
        session.refresh(access)
        return access, user.username


def get_user_by_token(token: str) -> Optional[User]:
    if not token:
        return None

    with get_session() as session:
        auth_token = session.exec(select(AuthToken).where(AuthToken.token == token)).first()
        if not auth_token or auth_token.revoked_at is not None or _is_expired(auth_token.expires_at):
            return None

        return session.exec(select(User).where(User.id == auth_token.user_id)).first()


def get_current_user(authorization: str = Header(default="")) -> User:
    token = ""
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def logout_token(access_token: str = "", refresh_token: str = "") -> None:
    with get_session() as session:
        if access_token:
            auth_token = session.exec(select(AuthToken).where(AuthToken.token == access_token)).first()
            if auth_token and auth_token.revoked_at is None:
                auth_token.revoked_at = _now()
                session.add(auth_token)

        if refresh_token:
            ref_token = session.exec(select(RefreshToken).where(RefreshToken.token == refresh_token)).first()
            if ref_token and ref_token.revoked_at is None:
                ref_token.revoked_at = _now()
                session.add(ref_token)

        session.commit()

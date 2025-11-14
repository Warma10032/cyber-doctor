from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import jwt
from django.conf import settings

from .token_store import token_store
from users.models import User


class TokenError(Exception):
    """Raised when a token is invalid or cannot be used."""


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime

    @property
    def access_expires_in(self) -> int:
        return max(int((self.access_expires_at - _now()).total_seconds()), 0)

    @property
    def refresh_expires_in(self) -> int:
        return max(int((self.refresh_expires_at - _now()).total_seconds()), 0)


def generate_token_pair(user: User) -> TokenPair:
    now = _now()
    access_expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_LIFETIME_MINUTES)
    refresh_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_LIFETIME_DAYS)

    access_payload = _build_payload(
        user=user,
        token_type="access",
        expires_at=access_expires_at,
    )
    refresh_payload = _build_payload(
        user=user,
        token_type="refresh",
        expires_at=refresh_expires_at,
    )

    access_token = jwt.encode(
        access_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    refresh_token = jwt.encode(
        refresh_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    token_store.store_refresh(
        refresh_payload["jti"],
        str(user.uid),
        int((refresh_expires_at - now).total_seconds()),
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )


def refresh_from_token(refresh_token: str) -> Tuple[User, TokenPair]:
    payload = decode_token(refresh_token, expected_type="refresh")
    owner = token_store.get_refresh_owner(payload["jti"])
    if owner is None or owner != payload["sub"]:
        raise TokenError("Refresh token has been revoked")

    try:
        user = User.objects.get(uid=payload["sub"])
    except User.DoesNotExist as exc:
        raise TokenError("User no longer exists") from exc

    # rotate refresh tokens: revoke old token once used
    token_store.revoke_refresh(payload["jti"])

    return user, generate_token_pair(user)


def revoke_tokens(access_token: str | None, refresh_token: str | None) -> None:
    if access_token:
        try:
            payload = decode_token(access_token, expected_type="access")
        except TokenError:
            payload = None
        if payload:
            ttl = max(int(payload["exp"] - _now().timestamp()), 0)
            token_store.blacklist_access(payload["jti"], ttl)

    if refresh_token:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError:
            payload = None
        if payload:
            token_store.revoke_refresh(payload["jti"])


def decode_token(token: str, expected_type: str | None = None) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc

    if expected_type and payload.get("type") != expected_type:
        raise TokenError("Incorrect token type")

    if payload.get("type") == "access" and token_store.is_access_blacklisted(payload.get("jti", "")):
        raise TokenError("Token has been revoked")

    return payload


def _build_payload(
    *,
    user: User,
    token_type: str,
    expires_at: datetime,
) -> Dict[str, Any]:
    now = _now()
    return {
        "jti": str(uuid.uuid4()),
        "type": token_type,
        "exp": int(expires_at.timestamp()),
        "iat": int(now.timestamp()),
        "sub": str(user.uid),
        "username": user.account,
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)

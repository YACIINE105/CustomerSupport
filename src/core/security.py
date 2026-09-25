from datetime import datetime, timedelta, timezone
from functools import lru_cache

import jwt
from pwdlib import PasswordHash

from src.core.config import Settings
from src.core.exceptions import ApplicationError, AuthenticationError

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    return hash_password("not-a-real-account-password")


def verify_password(password: str, password_hash: str | None) -> bool:
    # Missing users still perform a password-hash verification.
    return password_hasher.verify(password, password_hash or dummy_password_hash())


def signing_key(settings: Settings) -> str:
    if not settings.jwt_secret_key:
        raise ApplicationError("Authentication is not configured", status_code=503, code="auth_not_configured")
    return settings.jwt_secret_key


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(user_id), "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience, "token_type": "access",
    }, signing_key(settings), algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> int:
    key = signing_key(settings)
    try:
        claims = jwt.decode(
            token, key, algorithms=["HS256"], issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "exp", "iat", "iss", "aud", "token_type"]},
        )
        user_id = int(claims["sub"])
        if claims["token_type"] != "access" or not 0 < user_id <= 2147483647:
            raise ValueError("Invalid access token")
        return user_id
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise AuthenticationError() from exc

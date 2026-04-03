import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

# Note: override these with environment variables in production.
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "your-super-secret-key-change-in-production-use-secrets-token-hex-32"
)
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """Create a long-lived JWT refresh token. Returns (token, expiry datetime)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises JWTError on any failure (expired, bad signature, malformed).
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token, enforcing type == 'access'."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Invalid token type: expected access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    """Decode and validate a refresh token, enforcing type == 'refresh'."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type: expected refresh token")
    return payload


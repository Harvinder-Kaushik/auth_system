import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt
from app.logging_config import logger

# Load environment variables
load_dotenv()

# Validate required environment variables
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    logger.error("JWT_SECRET_KEY environment variable is not set")
    raise ValueError("JWT_SECRET_KEY environment variable must be set")

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


def create_generic_token(
    data: dict,
    token_type: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """
    Create a generic JWT token with specified type and expiration.
    Returns (token, expiry_datetime).
    """
    to_encode = data.copy()
    
    # Default expiration based on token type
    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        elif token_type == "refresh":
            expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        elif token_type == "password_reset":
            expires_delta = timedelta(hours=1)
        elif token_type == "email_verification":
            expires_delta = timedelta(hours=24)
        else:
            expires_delta = timedelta(minutes=30)
    
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_token_with_type(token: str, expected_type: str) -> dict:
    """Decode and validate a token, enforcing a specific type."""
    payload = decode_token(token)
    if payload.get("type") != expected_type:
        raise JWTError(f"Invalid token type: expected {expected_type}")
    return payload


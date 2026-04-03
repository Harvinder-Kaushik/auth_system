from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from app.database import get_db
from app.dependencies import get_current_user
from app.jwt_utils import create_access_token, create_refresh_token, decode_refresh_token
from app.models import RefreshToken, User
from app.schemas import (
    AccessTokenResponse,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive access + refresh tokens",
)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token_str, expires_at = create_refresh_token(token_data)

    # Persist refresh token in DB (so it can be revoked individually).
    db_token = RefreshToken(
        token=refresh_token_str,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token_str)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout by revoking a refresh token",
)
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> MessageResponse:
    db_token = db.query(RefreshToken).filter(RefreshToken.token == payload.refresh_token).first()
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found",
        )

    if db_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token has already been revoked",
        )

    db_token.is_revoked = True
    db.commit()
    return MessageResponse(message="Successfully logged out")


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Exchange a valid refresh token for a new access token",
)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_payload = decode_refresh_token(payload.refresh_token)
        user_id = token_payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    db_token = (
        db.query(RefreshToken)
        .filter(
            and_(
                RefreshToken.token == payload.refresh_token,
                RefreshToken.is_revoked.is_(False),
            )
        )
        .first()
    )
    if not db_token:
        raise credentials_exception

    # DB-level expiry as a second line of defense.
    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        db_token.is_revoked = True
        db.commit()
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise credentials_exception

    new_access_token = create_access_token({"sub": str(user.id)})
    return AccessTokenResponse(access_token=new_access_token)


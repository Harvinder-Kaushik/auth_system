from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from app.database import get_db
from app.dependencies import get_current_user
from app.jwt_utils import (
    create_access_token,
    create_refresh_token,
    create_generic_token,
    decode_refresh_token,
    decode_token_with_type,
)
from app.logging_config import logger
from app.models import PasswordResetToken, RefreshToken, User
from app.rate_limit import limiter
from app.schemas import (
    AccessTokenResponse,
    ChangePasswordRequest,
    MessageResponse,
    PasswordReset,
    PasswordResetRequest,
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
        logger.warning(f"Registration attempt with existing email: {payload.email}")
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
    logger.info(f"New user registered: {user.email}")
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive access + refresh tokens",
)
@limiter.limit("5/minute")
def login(
    request,
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(f"Failed login attempt for email: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {payload.email}")
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

    logger.info(f"User logged in: {user.email}")
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
        logger.warning("Logout attempt with invalid refresh token")
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
    logger.info(f"User logged out: {db_token.user_id}")
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
        logger.warning("Failed token refresh with invalid token")
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
        logger.warning(f"Refresh token expired for user: {user_id}")
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise credentials_exception

    new_access_token = create_access_token({"sub": str(user.id)})
    logger.info(f"Token refreshed for user: {user.email}")
    return AccessTokenResponse(access_token=new_access_token)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password for authenticated user",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.hashed_password):
        logger.warning(f"Failed password change attempt for user: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    logger.info(f"Password changed for user: {current_user.email}")
    return MessageResponse(message="Password changed successfully")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset link",
)
@limiter.limit("3/hour")
def forgot_password(
    request,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    
    # Always return same message for security (don't reveal if email exists)
    if not user:
        logger.info(f"Password reset attempt for non-existent email: {payload.email}")
        return MessageResponse(
            message="If email exists, a password reset link has been sent"
        )

    # Generate password reset token (valid for 1 hour)
    reset_token, expires_at = create_generic_token(
        data={"sub": str(user.id)},
        token_type="password_reset",
        expires_delta=timedelta(hours=1),
    )

    db_reset = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=expires_at,
    )
    db.add(db_reset)
    db.commit()

    logger.info(f"Password reset token generated for user: {user.email}")
    
    # TODO: Send email with reset link
    # Example email would contain: http://frontend.com/reset-password?token={reset_token}

    return MessageResponse(
        message="If email exists, a password reset link has been sent"
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with reset token",
)
@limiter.limit("5/hour")
def reset_password(
    request,
    payload: PasswordReset,
    db: Session = Depends(get_db),
) -> MessageResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token",
    )

    try:
        token_payload = decode_token_with_type(payload.token, "password_reset")
        user_id = token_payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        logger.warning("Failed password reset with invalid token")
        raise credentials_exception

    # Verify reset token exists in database and hasn't been used
    reset_record = (
        db.query(PasswordResetToken)
        .filter(
            and_(
                PasswordResetToken.token == payload.token,
                PasswordResetToken.is_used.is_(False),
            )
        )
        .first()
    )

    if not reset_record:
        logger.warning(f"Password reset attempt with invalid/used token for user: {user_id}")
        raise credentials_exception

    # Check if token has expired
    expires_at = reset_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        logger.warning(f"Password reset attempt with expired token for user: {user_id}")
        raise credentials_exception

    # Get user and update password
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise credentials_exception

    user.hashed_password = hash_password(payload.new_password)
    reset_record.is_used = True
    db.commit()

    logger.info(f"Password reset successful for user: {user.email}")
    return MessageResponse(message="Password reset successful")


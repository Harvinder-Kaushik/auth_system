import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, RefreshToken, PasswordResetToken


class TestRegistration:
    """Test user registration endpoint."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "ValidPassword123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["is_active"] is True

    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with duplicate email."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "ValidPassword123",
            },
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    def test_register_weak_password(self, client: TestClient):
        """Test registration with weak password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "weak",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "ValidPassword123",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Test user login endpoint."""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "Test1234",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_email(self, client: TestClient):
        """Test login with non-existent email."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123",
            },
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with wrong password."""
        response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123",
            },
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, test_user_inactive: User):
        """Test login with inactive user."""
        response = client.post(
            "/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "Test1234",
            },
        )
        assert response.status_code == 403
        assert "Inactive user account" in response.json()["detail"]

    def test_login_email_case_insensitive(self, client: TestClient, test_user: User):
        """Test that login works with different email cases."""
        response = client.post(
            "/auth/login",
            json={
                "email": "TEST@EXAMPLE.COM",
                "password": "Test1234",
            },
        )
        assert response.status_code == 200


class TestGetCurrentUser:
    """Test getting current authenticated user."""

    def test_get_me_success(self, client: TestClient, test_tokens: dict):
        """Test getting current user with valid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {test_tokens['access_token']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_get_me_no_token(self, client: TestClient):
        """Test getting current user without token."""
        response = client.get("/auth/me")
        assert response.status_code == 403

    def test_get_me_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 403


class TestRefreshToken:
    """Test token refresh endpoint."""

    def test_refresh_success(self, client: TestClient, test_tokens: dict):
        """Test successful token refresh."""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": test_tokens["refresh_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(self, client: TestClient):
        """Test refresh with invalid token."""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 401


class TestLogout:
    """Test logout endpoint."""

    def test_logout_success(self, client: TestClient, test_tokens: dict):
        """Test successful logout."""
        response = client.post(
            "/auth/logout",
            json={"refresh_token": test_tokens["refresh_token"]},
        )
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]

    def test_logout_invalid_token(self, client: TestClient):
        """Test logout with invalid token."""
        response = client.post(
            "/auth/logout",
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 404

    def test_logout_already_revoked(self, client: TestClient, test_tokens: dict):
        """Test logout with already revoked token."""
        # Logout first time
        response1 = client.post(
            "/auth/logout",
            json={"refresh_token": test_tokens["refresh_token"]},
        )
        assert response1.status_code == 200

        # Try to logout second time
        response2 = client.post(
            "/auth/logout",
            json={"refresh_token": test_tokens["refresh_token"]},
        )
        assert response2.status_code == 400


class TestChangePassword:
    """Test change password endpoint."""

    def test_change_password_success(self, client: TestClient, test_tokens: dict):
        """Test successful password change."""
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {test_tokens['access_token']}"},
            json={
                "current_password": "Test1234",
                "new_password": "NewPass4567",
            },
        )
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]

    def test_change_password_wrong_current(self, client: TestClient, test_tokens: dict):
        """Test change password with wrong current password."""
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {test_tokens['access_token']}"},
            json={
                "current_password": "WrongPassword123",
                "new_password": "NewPass4567",
            },
        )
        assert response.status_code == 401

    def test_change_password_weak_new_password(
        self, client: TestClient, test_tokens: dict
    ):
        """Test change password with weak new password."""
        response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {test_tokens['access_token']}"},
            json={
                "current_password": "Test1234",
                "new_password": "weak",
            },
        )
        assert response.status_code == 422

    def test_change_password_no_token(self, client: TestClient):
        """Test change password without token."""
        response = client.post(
            "/auth/change-password",
            json={
                "current_password": "Test1234",
                "new_password": "NewPass4567",
            },
        )
        assert response.status_code == 403


class TestForgotPassword:
    """Test forgot password endpoint."""

    def test_forgot_password_success(self, client: TestClient, test_user: User):
        """Test successful forgot password request."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200
        assert "reset link has been sent" in response.json()["message"]

    def test_forgot_password_nonexistent_email(self, client: TestClient):
        """Test forgot password with non-existent email."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        # Should return success message for security
        assert response.status_code == 200
        assert "reset link has been sent" in response.json()["message"]

    def test_forgot_password_creates_token(
        self, client: TestClient, test_user: User, db: Session
    ):
        """Test that forgot password creates a reset token in DB."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 200

        # Verify token was created
        token = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == test_user.id
        ).first()
        assert token is not None
        assert token.is_used is False


class TestResetPassword:
    """Test password reset endpoint."""

    def test_reset_password_success(
        self, client: TestClient, test_user: User, db: Session
    ):
        """Test successful password reset."""
        # First, create a reset token
        response1 = client.post(
            "/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        assert response1.status_code == 200

        # Get the token from DB
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == test_user.id
        ).first()
        token_value = reset_token.token

        # Now reset password
        response2 = client.post(
            "/auth/reset-password",
            json={
                "token": token_value,
                "new_password": "NewReset456",
            },
        )
        assert response2.status_code == 200
        assert "Password reset successful" in response2.json()["message"]

        # Verify token is marked as used
        used_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token_value
        ).first()
        assert used_token.is_used is True

    def test_reset_password_invalid_token(self, client: TestClient):
        """Test password reset with invalid token."""
        response = client.post(
            "/auth/reset-password",
            json={
                "token": "invalid_token",
                "new_password": "NewPass456",
            },
        )
        assert response.status_code == 400

    def test_reset_password_weak_password(
        self, client: TestClient, test_user: User, db: Session
    ):
        """Test password reset with weak new password."""
        # Create a reset token
        client.post(
            "/auth/forgot-password",
            json={"email": "test@example.com"},
        )
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == test_user.id
        ).first()

        # Try to reset with weak password
        response = client.post(
            "/auth/reset-password",
            json={
                "token": reset_token.token,
                "new_password": "weak",
            },
        )
        assert response.status_code == 422

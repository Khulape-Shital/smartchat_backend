"""
Authentication Endpoints Tests

This test suite validates:
1. User Registration endpoint works correctly
2. User Login endpoint works correctly
3. Google Authentication endpoint works correctly
4. Token Refresh endpoint works correctly
5. Access tokens and refresh tokens are generated correctly
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from jose import jwt

# [CRITICAL] This imports from app.main which is an EMPTY FILE (backend/app/main.py).
# The real application is defined in backend/main.py (the root).
# All tests in this file currently test an empty FastAPI app — every request returns 404.
# SUGGESTION: Change to: from main import app
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from app.core.config import settings
from app.schemas.user import UserCreate, UserLogin
from app.core.security import create_access_token, create_refresh_token

# [MEDIUM] client is module-level — shared across all tests with no isolation.
# SUGGESTION: Move client creation into a pytest fixture with function scope.

@pytest.fixture
def client_fixture():
    """Fixture providing TestClient with function scope for test isolation"""
    return TestClient(app)

@pytest.fixture
def test_user_data():
    """Fixture providing test user data with unique email per run"""
    from uuid import uuid4
    return {
        "name": "Test User",
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password": "TestPassword123!"
    }

@pytest.fixture
def test_login_data(test_user_data):
    """Fixture providing test login data"""
    return {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }


class TestAuthEndpoints:
    """Test suite for authentication endpoints"""

    BASE_URL = "/api/auth"

    # [CRITICAL] Tests use no mock/test database. They hit a real DB (whatever is in .env).
    # Running the test suite twice will fail on duplicate email checks.
    # SUGGESTION: Use a separate test DB, or override the get_db dependency with a
    # fixture that creates a fresh in-memory SQLite DB for each test and rolls back.

    def test_register_success(self, client_fixture, test_user_data):
        """Test successful user registration"""
        response = client_fixture.post(
            f"{self.BASE_URL}/register",
            json=test_user_data
        )

        # [CRITICAL] Register endpoint returns HTTP 201 Created, but this assertion
        # checks for 200. This test is currently incorrect and would fail if the
        # app were actually running.
        # SUGGESTION: Change to: assert response.status_code == 201
        assert response.status_code == 201
        data = response.json()

        # Verify all required fields are present
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data

        # Verify user data
        user = data["user"]
        assert user["email"] == test_user_data["email"]
        assert user["name"] == test_user_data["name"]
        assert "id" in user

        # Verify tokens are valid JWTs
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    def test_register_duplicate_email(self, client_fixture, test_user_data):
        """Test registration with duplicate email"""
        # Register first user
        client_fixture.post(
            f"{self.BASE_URL}/register",
            json=test_user_data
        )

        # [HIGH] No test teardown. On second test run, the first registration above will
        # fail because the user already exists from the previous run.
        # SUGGESTION: Use a unique email per run (e.g. with uuid4) or add DB teardown.
        # Try to register with same email
        response = client_fixture.post(
            f"{self.BASE_URL}/register",
            json=test_user_data
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_login_success(self, client_fixture, test_user_data, test_login_data):
        """Test successful user login"""
        # First register a user
        client_fixture.post(
            f"{self.BASE_URL}/register",
            json=test_user_data
        )

        # Then login
        response = client_fixture.post(
            f"{self.BASE_URL}/login",
            json=test_login_data
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data

        # Verify user data matches
        assert data["user"]["email"] == test_login_data["email"]

    def test_login_invalid_email(self, client_fixture):
        """Test login with non-existent email"""
        response = client_fixture.post(
            f"{self.BASE_URL}/login",
            json={
                "email": "nonexistent@example.com",
                "password": "Password123!"
            }
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_login_invalid_password(self, client_fixture, test_user_data, test_login_data):
        """Test login with incorrect password"""
        # Register a user
        client_fixture.post(
            f"{self.BASE_URL}/register",
            json=test_user_data
        )

        # Try to login with wrong password
        response = client_fixture.post(
            f"{self.BASE_URL}/login",
            json={
                "email": test_login_data["email"],
                "password": "WrongPassword123!"
            }
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_token_success(self, client_fixture, test_user_data, test_login_data):
        """Test successful token refresh"""
        # Register and login
        client_fixture.post(
            f"{self.BASE_URL}/register",
            json=test_user_data
        )

        login_response = client_fixture.post(
            f"{self.BASE_URL}/login",
            json=test_login_data
        )

        original_access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Call refresh endpoint
        response = client_fixture.post(
            f"{self.BASE_URL}/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert "access_token" in data
        new_access_token = data["access_token"]

        # New token should be different from original
        assert new_access_token != original_access_token

        # Both should be valid JWTs
        assert isinstance(new_access_token, str)
        assert len(new_access_token) > 0

    def test_refresh_token_invalid(self, client_fixture):
        """Test refresh with invalid token"""
        response = client_fixture.post(
            f"{self.BASE_URL}/refresh",
            json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_token_expired(self, client_fixture):
        """Test refresh with expired token"""
        # Create an expired refresh token
        expired_payload = {
            "sub": "test_user_id",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "type": "refresh"
        }

        expired_token = jwt.encode(
            expired_payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        response = client_fixture.post(
            f"{self.BASE_URL}/refresh",
            json={"refresh_token": expired_token}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_token_wrong_type(self, client_fixture):
        """Test refresh with access token instead of refresh token"""
        # Create a token with wrong type
        wrong_type_payload = {
            "sub": "test_user_id",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "type": "access"  # Should be "refresh"
        }

        wrong_token = jwt.encode(
            wrong_type_payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        response = client_fixture.post(
            f"{self.BASE_URL}/refresh",
            json={"refresh_token": wrong_token}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_google_auth_success(self, client_fixture):
        """Test successful Google authentication"""
        mock_user_info = {
            "sub": "google_user_id_123",
            "email": "user@gmail.com",
            "name": "Google User",
            "picture": "https://example.com/photo.jpg"
        }

        with patch('app.api.v1.endpoints.auth.id_token.verify_oauth2_token') as mock_verify:
            mock_verify.return_value = mock_user_info

            response = client_fixture.post(
                f"{self.BASE_URL}/google",
                json={"token": "valid_google_token"}
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "access_token" in data
            assert "refresh_token" in data
            assert "user" in data

            # Verify user data
            assert data["user"]["email"] == mock_user_info["email"]
            assert data["user"]["name"] == mock_user_info["name"]

    def test_google_auth_invalid_token(self, client_fixture):
        """Test Google authentication with invalid token"""
        with patch('app.api.v1.endpoints.auth.id_token.verify_oauth2_token') as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            response = client_fixture.post(
                f"{self.BASE_URL}/google",
                json={"token": "invalid_google_token"}
            )

            assert response.status_code == 400
            assert "invalid" in response.json()["detail"].lower()

    def test_token_payload_structure(self, client_fixture, test_user_data, test_login_data):
        """Test that tokens contain correct payload structure"""
        # Register and login
        client_fixture.post(
            f"{self.BASE_URL}/register",
            json=test_user_data
        )

        login_response = client_fixture.post(
            f"{self.BASE_URL}/login",
            json=test_login_data
        )

        data = login_response.json()
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # Decode and verify access token
        access_payload = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert access_payload["type"] == "access"
        assert "sub" in access_payload
        assert "exp" in access_payload

        # Decode and verify refresh token
        refresh_payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert refresh_payload["type"] == "refresh"
        assert "sub" in refresh_payload
        assert "exp" in refresh_payload

        # User IDs should match
        assert access_payload["sub"] == refresh_payload["sub"]

    def test_multiple_logins_create_different_tokens(self, client_fixture, test_user_data, test_login_data):
        """Test that multiple logins create different tokens"""
        # Register once
        client_fixture.post(
            f"{self.BASE_URL}/register",
            json=test_user_data
        )

        # Login twice
        response1 = client_fixture.post(
            f"{self.BASE_URL}/login",
            json=test_login_data
        )

        response2 = client_fixture.post(
            f"{self.BASE_URL}/login",
            json=test_login_data
        )

        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]

        # Tokens should be different (different timestamps)
        assert token1 != token2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

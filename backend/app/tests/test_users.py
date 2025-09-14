"""Comprehensive tests for user authentication endpoints"""

import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
import httpx
from httpx import AsyncClient, ASGITransport
from bson import ObjectId
import jwt

from app.main import app
from app.core.security import hash_password, create_access_token, JWT_SECRET, JWT_ALGORITHM


@pytest.mark.asyncio
class TestUserAuthentication:
    """Test class for user authentication endpoints"""

    @pytest_asyncio.fixture
    async def mock_db_with_user(self):
        """Create a mock database with a test user"""
        mock_db = AsyncMock()
        mock_users_collection = AsyncMock()
        
        # Mock user data
        test_user_id = ObjectId()
        test_user = {
            "_id": test_user_id,
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": hash_password("password123"),
            "role": "user",
            "created_at": datetime.utcnow(),
            "last_login": None,
            "disabled": False
        }
        
        mock_db.users = mock_users_collection
        mock_users_collection.find_one.return_value = test_user
        mock_users_collection.insert_one.return_value = AsyncMock(inserted_id=test_user_id)
        mock_users_collection.update_one.return_value = AsyncMock(modified_count=1)
        
        return mock_db, test_user

    async def test_signup_success(self):
        """Test successful user signup"""
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_users_collection = AsyncMock()
            mock_db.users = mock_users_collection
            
            # Mock successful insertion
            test_user_id = ObjectId()
            mock_users_collection.insert_one.return_value = AsyncMock(inserted_id=test_user_id)
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/users/signup",
                    json={
                        "username": "newuser",
                        "email": "newuser@example.com",
                        "password": "password123"
                    }
                )
            
            assert response.status_code == 201
            data = response.json()
            
            assert "id" in data
            assert data["username"] == "newuser" 
            assert data["email"] == "newuser@example.com"
            assert data["role"] == "user"
            assert "token" in data
            
            # Verify token is valid
            token_payload = jwt.decode(data["token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            assert token_payload["sub"] == str(test_user_id)
            assert token_payload["username"] == "newuser"

    async def test_signup_duplicate_email(self):
        """Test signup with duplicate email"""
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_users_collection = AsyncMock()
            mock_db.users = mock_users_collection
            
            # Mock duplicate key error
            from pymongo.errors import DuplicateKeyError
            mock_users_collection.insert_one.side_effect = DuplicateKeyError("email_1 dup key")
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/users/signup",
                    json={
                        "username": "testuser",
                        "email": "test@example.com",
                        "password": "password123"
                    }
                )
            
            assert response.status_code == 409
            error_data = response.json()
            assert "email already registered" in error_data["error"]["detail"].lower()

    async def test_signup_duplicate_username(self):
        """Test signup with duplicate username"""
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_users_collection = AsyncMock()
            mock_db.users = mock_users_collection
            
            # Mock duplicate key error
            from pymongo.errors import DuplicateKeyError
            mock_users_collection.insert_one.side_effect = DuplicateKeyError("username_1 dup key")
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/users/signup",
                    json={
                        "username": "existinguser",
                        "email": "new@example.com",
                        "password": "password123"
                    }
                )
            
            assert response.status_code == 409
            error_data = response.json()
            assert "username already taken" in error_data["error"]["detail"].lower()

    async def test_signup_validation_errors(self):
        """Test signup with validation errors"""
        test_cases = [
            # Missing username
            {
                "email": "test@example.com",
                "password": "password123"
            },
            # Missing email
            {
                "username": "testuser",
                "password": "password123"
            },
            # Missing password
            {
                "username": "testuser",
                "email": "test@example.com"
            },
            # Username too short
            {
                "username": "ab",
                "email": "test@example.com",
                "password": "password123"
            },
            # Password too short
            {
                "username": "testuser",
                "email": "test@example.com",
                "password": "short"
            },
            # Invalid email
            {
                "username": "testuser",
                "email": "invalid-email",
                "password": "password123"
            }
        ]
        
        for test_case in test_cases:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/v1/users/signup", json=test_case)
            
            assert response.status_code == 422  # Validation error

    async def test_login_success(self, mock_db_with_user):
        """Test successful login"""
        mock_db, test_user = mock_db_with_user
        
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/users/login",
                    json={
                        "email": "test@example.com",
                        "password": "password123"
                    }
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert data["role"] == "user"
            assert "token" in data
            
            # Verify token is valid
            token_payload = jwt.decode(data["token"], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            assert token_payload["sub"] == str(test_user["_id"])

    async def test_login_invalid_email(self):
        """Test login with non-existent email"""
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_users_collection = AsyncMock()
            mock_db.users = mock_users_collection
            mock_users_collection.find_one.return_value = None  # User not found
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/users/login",
                    json={
                        "email": "nonexistent@example.com",
                        "password": "password123"
                    }
                )
            
            assert response.status_code == 401
            error_data = response.json()
            assert "invalid email or password" in error_data["error"]["detail"].lower()

    async def test_login_invalid_password(self, mock_db_with_user):
        """Test login with wrong password"""
        mock_db, test_user = mock_db_with_user
        
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/users/login",
                    json={
                        "email": "test@example.com",
                        "password": "wrongpassword"
                    }
                )
            
            assert response.status_code == 401
            error_data = response.json()
            assert "invalid email or password" in error_data["error"]["detail"].lower()

    async def test_login_disabled_account(self, mock_db_with_user):
        """Test login with disabled account"""
        mock_db, test_user = mock_db_with_user
        test_user["disabled"] = True  # Disable the account
        
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/v1/users/login",
                    json={
                        "email": "test@example.com",
                        "password": "password123"
                    }
                )
            
            assert response.status_code == 401
            error_data = response.json()
            assert "account disabled" in error_data["error"]["detail"].lower()

    async def test_get_me_success(self, mock_db_with_user):
        """Test successful /me endpoint with valid token"""
        mock_db, test_user = mock_db_with_user
        
        # Create valid token
        token = create_access_token(sub=str(test_user["_id"]), data={"username": "testuser"})
        
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/v1/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert data["role"] == "user"
            assert "token" not in data  # Profile response shouldn't include token

    async def test_get_me_invalid_token(self):
        """Test /me endpoint with invalid token"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/users/me",
                headers={"Authorization": "Bearer invalid_token"}
            )
        
        assert response.status_code == 401
        error_data = response.json()
        assert "invalid token" in error_data["error"]["detail"].lower()

    async def test_get_me_missing_token(self):
        """Test /me endpoint without Authorization header"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/users/me")
        
        assert response.status_code == 403  # Missing credentials

    async def test_get_me_expired_token(self):
        """Test /me endpoint with expired token"""
        # Create expired token (expires in -1 minutes)
        expired_token = create_access_token(
            sub="test_user_id", 
            data={"username": "testuser"},
            expires_minutes=-1
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/users/me",
                headers={"Authorization": f"Bearer {expired_token}"}
            )
        
        assert response.status_code == 401
        error_data = response.json()
        assert "expired" in error_data["error"]["detail"].lower()

    async def test_get_me_user_not_found(self):
        """Test /me endpoint when user no longer exists"""
        # Create valid token for non-existent user
        token = create_access_token(sub=str(ObjectId()), data={"username": "deleteduser"})
        
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_users_collection = AsyncMock()
            mock_db.users = mock_users_collection
            mock_users_collection.find_one.return_value = None  # User not found
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/v1/users/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
            
            assert response.status_code == 401
            error_data = response.json()
            assert "user not found" in error_data["error"]["detail"].lower()

    async def test_password_hashing(self):
        """Test that passwords are properly hashed and not stored in plaintext"""
        from app.core.security import hash_password, verify_password
        
        password = "test_password_123"
        hashed = hash_password(password)
        
        # Verify hash is different from original password
        assert hashed != password
        
        # Verify hash can be verified
        assert verify_password(password, hashed) is True
        
        # Verify wrong password fails
        assert verify_password("wrong_password", hashed) is False

    async def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification"""
        from app.core.security import create_access_token, verify_access_token
        
        user_id = str(ObjectId())
        data = {"username": "testuser", "role": "user"}
        
        # Create token
        token = create_access_token(sub=user_id, data=data)
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token
        payload = verify_access_token(token)
        assert payload["sub"] == user_id
        assert payload["username"] == "testuser"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    async def test_integration_signup_login_me_flow(self):
        """Test complete signup -> login -> /me flow"""
        with patch('app.routes.user.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_users_collection = AsyncMock()
            mock_db.users = mock_users_collection
            
            test_user_id = ObjectId()
            test_user = {
                "_id": test_user_id,
                "username": "integrationuser",
                "email": "integration@example.com",
                "password_hash": hash_password("password123"),
                "role": "user",
                "created_at": datetime.utcnow(),
                "last_login": datetime.utcnow(),
                "disabled": False
            }
            
            # Mock signup
            mock_users_collection.insert_one.return_value = AsyncMock(inserted_id=test_user_id)
            
            # Mock login and /me
            mock_users_collection.find_one.return_value = test_user
            mock_users_collection.update_one.return_value = AsyncMock(modified_count=1)
            
            mock_get_db.return_value = mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # 1. Signup
                signup_response = await client.post(
                    "/v1/users/signup",
                    json={
                        "username": "integrationuser",
                        "email": "integration@example.com",
                        "password": "password123"
                    }
                )
                
                assert signup_response.status_code == 201
                signup_data = signup_response.json()
                signup_token = signup_data["token"]
                
                # 2. Login
                login_response = await client.post(
                    "/v1/users/login",
                    json={
                        "email": "integration@example.com",
                        "password": "password123"
                    }
                )
                
                assert login_response.status_code == 200
                login_data = login_response.json()
                login_token = login_data["token"]
                
                # 3. Get profile using login token
                me_response = await client.get(
                    "/v1/users/me",
                    headers={"Authorization": f"Bearer {login_token}"}
                )
                
                assert me_response.status_code == 200
                me_data = me_response.json()
                
                assert me_data["username"] == "integrationuser"
                assert me_data["email"] == "integration@example.com"
                assert me_data["role"] == "user"
"""User authentication routes for signup, login, and profile management"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
import logging

from app.db.mongo import get_database
from app.models.user import UserModel
from app.schemas.user import (
    UserSignupRequest, 
    UserLoginRequest, 
    UserResponse, 
    UserProfileResponse,
    ErrorResponse
)
from app.core.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    verify_access_token
)

router = APIRouter(tags=["users"])
logger = logging.getLogger(__name__)

# Security scheme for JWT token
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserModel:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        UserModel: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Verify token and extract payload
    payload = verify_access_token(credentials.credentials)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )
    
    # Get database and find user
    db = await get_database()
    users_collection = db.users
    
    try:
        user_doc = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user = UserModel.from_dict(user_doc)
        
        # Check if user is disabled
        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account disabled"
            )
        
        return user
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: UserSignupRequest):
    """
    Register a new user account
    
    Creates a new user with hashed password and returns JWT token.
    Email and username must be unique.
    
    Args:
        request: User signup data (username, email, password)
        
    Returns:
        UserResponse: User data with JWT token
        
    Raises:
        HTTPException: 409 if email/username already exists
    """
    logger.info(f"[UserRouter] Signup attempt for username={request.username}, email={request.email}")
    
    db = await get_database()
    users_collection = db.users
    
    try:
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create user document
        user_doc = {
            "username": request.username,
            "email": str(request.email),
            "password_hash": password_hash,
            "role": "user",
            "created_at": datetime.utcnow(),
            "last_login": None,
            "disabled": False
        }
        
        # Insert user into database
        result = await users_collection.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        # Create JWT token
        token = create_access_token(
            sub=user_id,
            data={"role": "user", "username": request.username}
        )
        
        logger.info(f"[UserRouter] Signup successful for username={request.username}, email={request.email}")
        
        return UserResponse(
            id=user_id,
            username=request.username,
            email=str(request.email),
            role="user",
            token=token
        )
        
    except DuplicateKeyError as e:
        # Handle unique constraint violations
        if "email" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        elif "username" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )
    except Exception as e:
        logger.error(f"Signup error for {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )
    
    try:
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create user document
        user_doc = {
            "username": request.username,
            "email": str(request.email),
            "password_hash": password_hash,
            "role": "user",
            "created_at": datetime.utcnow(),
            "last_login": None,
            "disabled": False
        }
        
        # Insert user into database
        result = await users_collection.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        # Create JWT token
        token = create_access_token(
            sub=user_id,
            data={"role": "user", "username": request.username}
        )
        
        logger.info(f"[UserRouter] Signup successful for username={request.username}, email={request.email}")
        
        return UserResponse(
            id=user_id,
            username=request.username,
            email=str(request.email),
            role="user",
            token=token
        )
        
    except DuplicateKeyError as e:
        # Handle unique constraint violations
        if "email" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        elif "username" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )
    except Exception as e:
        logger.error(f"Signup error for {request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )


@router.post("/login", response_model=UserResponse)
async def login(request: UserLoginRequest):
    """
    Authenticate user and return JWT token
    
    Validates credentials and updates last_login timestamp.
    
    Args:
        request: User login credentials (email, password)
        
    Returns:
        UserResponse: User data with JWT token
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    logger.info(f"[UserRouter] Login attempt for email={request.email}")
    
    db = await get_database()
    users_collection = db.users
    
    try:
        # Find user by email
        user_doc = await users_collection.find_one({"email": str(request.email)})
        
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        user = UserModel.from_dict(user_doc)
        
        # Check if account is disabled
        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account disabled"
            )
        
        # Verify password
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        await users_collection.update_one(
            {"_id": user.id},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Create JWT token
        token = create_access_token(
            sub=str(user.id),
            data={"role": user.role, "username": user.username}
        )
        
        logger.info(f"[UserRouter] Login successful for username={user.username}, email={user.email}")
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            token=token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: UserModel = Depends(get_current_user)):
    """
    Get current authenticated user profile
    
    Protected endpoint that returns user profile based on JWT token.
    
    Args:
        current_user: Current authenticated user (from JWT token)
        
    Returns:
        UserProfileResponse: User profile data (without token)
    """
    return UserProfileResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )


# Optional: Admin endpoint to get user by ID (for testing)
@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(user_id: str, current_user: UserModel = Depends(get_current_user)):
    """
    Get user by ID (admin only or self)
    
    Args:
        user_id: User ID to fetch
        current_user: Current authenticated user
        
    Returns:
        UserProfileResponse: User profile data
        
    Raises:
        HTTPException: 403 if not admin and not self, 404 if user not found
    """
    # Allow users to fetch their own profile, admins can fetch any profile
    if str(current_user.id) != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    db = await get_database()
    users_collection = db.users
    
    try:
        user_doc = await users_collection.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = UserModel.from_dict(user_doc)
        
        return UserProfileResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user"
        )


@router.get("/debug-list", tags=["debug"])
async def debug_list_users():
    """Debug endpoint to see what users are stored in MongoDB"""
    try:
        db = await get_database()
        users_collection = db.users
        
        # Get all users from MongoDB
        users_cursor = users_collection.find({}, {"password_hash": 0})  # Exclude password hashes
        users_list = []
        
        async for user in users_cursor:
            user["_id"] = str(user["_id"])  # Convert ObjectId to string
            users_list.append(user)
        
        return {
            "mongodb_users_count": len(users_list),
            "users": users_list
        }
        
    except Exception as e:
        return {"error": f"Failed to query MongoDB: {str(e)}"}
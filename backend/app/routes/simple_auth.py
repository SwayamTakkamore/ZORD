"""
Simple test routes for debugging authentication

This is a simplified version to test the basic routing without complex dependencies.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
import logging

# Simple router without prefix conflicts
router = APIRouter(tags=["debug-auth"])

# Simple request/response models
class SimpleSignupRequest(BaseModel):
    username: str
    email: str
    password: str

class SimpleLoginRequest(BaseModel):
    email: str
    password: str

class SimpleResponse(BaseModel):
    message: str
    username: str
    email: str

# In-memory storage for testing
users_db = {}

logger = logging.getLogger(__name__)

@router.post("/signup")
async def simple_signup(request: SimpleSignupRequest):
    """Simple signup for testing"""
    logger.info(f"[SimpleAuth] Signup attempt: {request.username}, {request.email}")
    
    # Check if user exists
    if request.email in users_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Store user (simplified - no password hashing for testing)
    users_db[request.email] = {
        "username": request.username,
        "email": request.email,
        "password": request.password  # In production, this should be hashed!
    }
    
    logger.info(f"[SimpleAuth] Signup successful: {request.username}")
    
    return SimpleResponse(
        message="Signup successful",
        username=request.username,
        email=request.email
    )

@router.post("/login")
async def simple_login(request: SimpleLoginRequest):
    """Simple login for testing"""
    logger.info(f"[SimpleAuth] Login attempt: {request.email}")
    
    # Check if user exists
    if request.email not in users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user = users_db[request.email]
    
    # Check password (simplified - no hash verification for testing)
    if user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    logger.info(f"[SimpleAuth] Login successful: {user['username']}")
    
    return SimpleResponse(
        message="Login successful",
        username=user["username"],
        email=user["email"]
    )

@router.get("/debug/users")
async def debug_users():
    """Debug endpoint to see all users"""
    return {"users_count": len(users_db), "users": list(users_db.keys())}

@router.get("/debug/mongodb-users")
async def debug_mongodb_users():
    """Check what users are actually stored in MongoDB"""
    from app.db.mongo import get_database
    
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

@router.post("/test-db-signup")
async def test_db_signup(request: SimpleSignupRequest):
    """Test the actual database signup process"""
    print(f"DEBUG: Test DB signup called with username={request.username}, email={request.email}")
    
    from app.db.mongo import get_database
    from app.core.security import hash_password, create_access_token
    from datetime import datetime
    
    try:
        db = await get_database()
        users_collection = db.users
        print(f"DEBUG: Got database and users collection")
        
        # Hash password
        password_hash = hash_password(request.password)
        print(f"DEBUG: Password hashed successfully")
        
        # Create user document
        user_doc = {
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
            "role": "user",
            "created_at": datetime.utcnow(),
            "last_login": None,
            "disabled": False
        }
        print(f"DEBUG: User document created: {user_doc}")
        
        # Insert user into database
        result = await users_collection.insert_one(user_doc)
        user_id = str(result.inserted_id)
        print(f"DEBUG: User inserted with ID: {user_id}")
        
        # Create JWT token
        token = create_access_token(
            sub=user_id,
            data={"role": "user", "username": request.username}
        )
        print(f"DEBUG: JWT token created")
        
        return {
            "message": "Database signup successful",
            "username": request.username,
            "email": request.email,
            "user_id": user_id,
            "token": token
        }
        
    except Exception as e:
        print(f"DEBUG: Exception in test_db_signup: {type(e).__name__}: {e}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database signup test failed: {str(e)}"
        )